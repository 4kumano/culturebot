import asyncio
from datetime import datetime, timedelta
from typing import Union

import discord
from discord import Guild, Member, Message, Role, TextChannel
from discord.ext import commands
from discord.ext.commands import Bot, Context


class Moderation(commands.Cog, name="moderation"):
    """Moderation commands and shit"""

    def __init__(self, bot: Bot):
        self.bot = bot

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
    
    async def get_muted_role(self, guild: Guild) -> Role:
        """Returns the muted role or creates one."""
        role = discord.utils.find(lambda r: r.name.lower() == 'muted', guild.roles)
        
        if role is None:
            role = await guild.create_role(name='muted')
        # update mute perms
        overwrite = discord.PermissionOverwrite(
            send_messages=False,
            add_reactions=False
        )
        for channel in guild.text_channels:
            if channel.category and channel.permissions_synced:
                channel = channel.category
            await channel.set_permissions(role, overwrite=overwrite)
        
        return role

    @commands.command('mute')
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def mute(self, ctx: Context, member: Member, *, reason: str = None):
        """Mutes a member from all channels.

        They will not be able to speak until they are unmuted.
        """
        if member.bot:
            await ctx.send('Cannot mute a bot.')
            return
        role = await self.get_muted_role(ctx.guild) # type: ignore
        await member.add_roles(role, reason=reason)
        await ctx.send(f'Muted {member}')

    @commands.command('unmute')
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def unmute(self, ctx: Context, member: Member):
        """Unmutes a member from all channels."""
        role = await self.get_muted_role(ctx.guild) # type: ignore
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


def setup(bot):
    bot.add_cog(Moderation(bot))
