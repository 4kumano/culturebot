import asyncio
from datetime import datetime, timedelta
from typing import Union

import discord
from discord import Member, Message, Role, TextChannel
from discord.ext import commands
from discord.ext.commands import Context
from utils import CCog, get_muted_role


class Moderation(CCog, name="moderation"):
    """Moderation commands and shit"""
    @commands.command('purge')
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def purge(self, ctx: Context, limit: Union[Message, int] = 10):
        """Purges a set amount of messages from all users in the current channel
        
        If a message id is passed in, all messages up to the message exclusive will be purged.
        """
        if not isinstance(ctx.channel, discord.TextChannel):
            return # type check for dms
        
        if isinstance(limit, Message):
            deleted = await ctx.channel.purge(limit=None, after=limit)
        else:
            deleted = await ctx.channel.purge(limit=limit + 1)
        await ctx.send(f"Deleted {len(deleted)} messages.", delete_after=1)

    @commands.command('prune')
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def prune(self, ctx: Context, user: Member, days: int = 1, *channels: TextChannel):
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
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def mute(self, ctx: Context, member: Member, *, reason: str = None):
        """Mutes a member from all channels.

        They will not be able to speak until they are unmuted.
        """
        if ctx.guild is None:
            raise commands.NoPrivateMessage()
        if member.guild_permissions.administrator:
            await ctx.send('Cannot mute an admin')
            return
        role = await get_muted_role(ctx.guild)
        await member.add_roles(role, reason=reason)
        await ctx.send(f'Muted {member}')

    @commands.command('unmute')
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def unmute(self, ctx: Context, member: Member):
        """Unmutes a member from all channels."""
        if ctx.guild is None:
            raise commands.NoPrivateMessage()
        role = await get_muted_role(ctx.guild)
        if role not in member.roles:
            await ctx.send(f"{member} is not currently muted.")
            return
        await member.remove_roles(role)
        await ctx.send(f"Unmuted {member}")

    @commands.command('lock')
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def lock(self, ctx: Context, channel: TextChannel = None, *roles: Role):
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
    async def unlock(self, ctx: Context, channel: TextChannel = None, *roles: Role):
        """Unlocks a previously locked channel."""
        channel = channel or ctx.channel # type: ignore
        roles = roles or [ctx.guild.roles[0]] # type: ignore
        
        for role in roles:
            await channel.set_permissions(role, overwrite=None)
        
        await ctx.send(f':unlock: Unlocked {channel.mention}')
    
    @commands.command()
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def cleanup(self, ctx: Context):
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
