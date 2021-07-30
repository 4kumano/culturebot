from __future__ import annotations
import asyncio
from datetime import datetime, timedelta
from typing import Union
from utils.interaction import confirm

import discord
from discord.ext import commands
from utils import CCog, get_muted_role


class Moderation(CCog):
    """Moderation commands and shit"""
    @commands.command('purge')
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def purge(self, ctx: commands.Context, limit: Union[discord.Message, int] = 10):
        """Purges a set amount of messages from all users in the current channel
        
        If a message id is passed in, all messages up to the message exclusive will be purged.
        """
        assert isinstance(ctx.channel, discord.TextChannel)
        
        msg = await ctx.send(f"Are you sure you want to delete " + (f'**{limit}** messages in {ctx.channel.mention}' if isinstance(limit, int) else f'all messages up to {limit.id}'))
        if not await confirm(self.bot, msg, ctx.author):
            await ctx.send("Cancelled!")
            return
        
        if isinstance(limit, discord.Message):
            deleted = await ctx.channel.purge(limit=None, after=limit)
        else:
            deleted = await ctx.channel.purge(limit=limit + 2)
        await ctx.send(f"Deleted {len(deleted)} messages.", delete_after=1)

    @commands.command('prune')
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def prune(self, ctx: commands.Context, user: discord.Member, days: int = 1, *channels: discord.TextChannel):
        """Purges all messages from a user from the last 24 hours.

        Can specify which channels to purge.
        """
        channels = channels or ctx.guild.text_channels # type: ignore
        deleted = []
        for channel in channels:
            await ctx.send(f'Deleting messages from {channel.mention}')
            deleted += await channel.purge(
                limit=None,
                check=lambda m: m.author == user,
                after=datetime.now() - timedelta(days=days))
        await ctx.send(f"Deleted {len(deleted) - 1} messages.", delete_after=1)

    @commands.command('mute')
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def mute(self, ctx: commands.Context, member: discord.Member, *, reason: str = None):
        """Mutes a member from all channels.

        They will not be able to speak until they are unmuted.
        """
        assert ctx.guild is not None
        
        if member.guild_permissions.administrator:
            await ctx.send('Cannot mute an admin')
            return
        role = await get_muted_role(ctx.guild)
        await member.add_roles(role, reason=reason)
        await ctx.send(f'Muted {member}')

    @commands.command('unmute')
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def unmute(self, ctx: commands.Context, member: discord.Member):
        """Unmutes a member from all channels."""
        assert ctx.guild is not None
        
        role = await get_muted_role(ctx.guild)
        if role not in member.roles:
            await ctx.send(f"{member} is not currently muted.")
            return
        await member.remove_roles(role)
        await ctx.send(f"Unmuted {member}")

    @commands.command('lock')
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def lock(self, ctx: commands.Context, channel: discord.TextChannel = None, *roles: discord.Role):
        """Locks a channel for all members. 
        
        You can specify which roles to disallow
        """
        channel = channel or ctx.channel # type: ignore
        roles = roles or [ctx.guild.roles[0]] # type: ignore
        
        for role in roles:
            await channel.set_permissions(role, send_messages=False)

        msg = await ctx.send(f':lock: Locked {channel.mention}')
        await msg.add_reaction('↩️')
        try:
            await self.bot.wait_for(
                'raw_reaction_add', 
                check=lambda event: str(event.emoji) == '↩️' and event.user_id == ctx.author.id,
                timeout=12*60*60
            )
        except asyncio.TimeoutError:
            await msg.remove_reaction('↩️', ctx.me)
        else:
            await self.unlock.invoke(ctx)

    @commands.command('unlock')
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def unlock(self, ctx: commands.Context, channel: discord.TextChannel = None, *roles: discord.Role):
        """Unlocks a previously locked channel."""
        channel = channel or ctx.channel # type: ignore
        roles = roles or [ctx.guild.roles[0]] # type: ignore
        
        for role in roles:
            await channel.set_permissions(role, overwrite=None)
        
        await ctx.send(f':unlock: Unlocked {channel.mention}')
    
    @commands.command()
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def cleanup(self, ctx: commands.Context):
        """Goes through every channel and cleans up permissions"""
        assert ctx.guild is not None
        # cleanup permissions
        for channel in ctx.guild.channels:
            clean = {target:overwrite for target, overwrite in channel.overwrites.items() if not overwrite.is_empty()}
            if clean == channel.overwrites:
                continue # don't make extra requests
            
            await channel.edit(overwrites=clean)
            await ctx.send(f"Cleaned {channel.mention}")
        await ctx.send("Cleanup complete")
                


def setup(bot):
    bot.add_cog(Moderation(bot))
