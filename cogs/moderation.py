from datetime import datetime, timedelta
from typing import Optional
import discord
from discord import User, Member
from discord.channel import TextChannel
from discord.guild import Guild
from discord.permissions import PermissionOverwrite
from discord.role import Role
from config import config, logger
from discord.ext import commands
from discord.ext.commands import Bot, Context


class Moderation(commands.Cog, name="moderation"):
    """Moderation commands and shit"""

    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.command('purge')
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def purge(self, ctx: Context, limit: int = 10):
        """Purges a set amount of messages from all users in the current channel"""
        deleted = await ctx.channel.purge(limit=limit + 1)
        await ctx.send(f"Deleted {len(deleted)} messages.", delete_after=1)

    @commands.command('prune')
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def prune(self, ctx: Context, user: Member, *channels: TextChannel):
        """Purges all messages from a user from the last 24 hours.

        Can specify which channels to purge.
        """
        channels = channels or ctx.guild.channels
        deleted = []
        for channel in channels:
            deleted += await channel.purge(
                limit=None,
                check=lambda m: m.author == user,
                before=datetime.now() - timedelta(days=1))
        await ctx.send(f"Deleted {len(deleted)} messages.", delete_after=1)
    
    async def get_muted_role(self, guild: Guild, update: bool = True) -> Optional[Role]:
        """Returns the muted role or creates one."""
        role = discord.utils.find(lambda r: r.name.lower() == 'muted', guild.roles)
        if not update:
            return role

        if role is None:
            role = await guild.create_role(name='muted')
        # update mute perms
        overwrite = discord.PermissionOverwrite(
            send_messages=False,
            add_reactions=False
        )
        for channel in guild.text_channels:
            if channel.permissions_synced:
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
        role = await self.get_muted_role(ctx.guild)
        await member.add_roles(role, reason=reason)
        await ctx.send(f'Muted {member}')

    @commands.command('unmute')
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def unmute(self, ctx: Context, member: Member):
        """Unmutes a member from all channels."""
        role = await self.get_muted_role(ctx.guild, update=False)
        if role is None:
            await ctx.send("A muted role doesn't even exist.")
            return
        if role not in member.roles:
            await ctx.send(f"{member} is not currently muted.")
            return
        await member.remove_roles()
        await ctx.send(f"Unmuted {member}")

    @commands.command('lock')
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def lock(self, ctx: Context, channel: TextChannel = None):
        channel = channel or ctx.channel
        await ctx.send(f'Locked {channel.mention} :lock:')
        await channel.set_permissions(ctx.guild.roles[0], send_messages=False)

    @commands.command('unlock')
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def unlock(self, ctx: Context, channel: TextChannel = None):
        channel = channel or ctx.channel
        await channel.set_permissions(ctx.guild.roles[0], overwrite=None)
        await ctx.send(f'Unlocked {channel.mention} :unlock:')


def setup(bot):
    bot.add_cog(Moderation(bot))
