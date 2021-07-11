import time
from datetime import datetime

import discord
from discord import Guild
from discord.ext import commands
from discord.ext.commands import Context
from utils import CCog, humandate, humandelta

class General(CCog, name="general"):
    """General all-purpose commands every bot has"""
    
    @commands.command(aliases=["botinfo"])
    async def info(self, ctx: commands.Context):
        """Basic info about the bot.

        Stuff like the author.
        """
        app = await self.bot.application_info()
        embed = discord.Embed(
            title="Culture bot.",
            description=f"A multi-purpose bot made by sadru, contains random features I decided to add on a whim.",
            color=0x42F56C
        ).set_thumbnail(
            url=self.bot.user.avatar_url
        ).set_author(
            name=self.bot.user.name,
            icon_url=self.bot.user.avatar_url
        ).add_field(
            name="Owner:",
            value=app.owner.mention
        ).add_field(
            name="Prefix:",
            value=f"`{self.bot.config['bot']['prefix']}` or {self.bot.user.mention}"
        ).add_field(
            name="Source code (python):",
            value="[thesadru/culturebot](https://github.com/thesadru/culturebot)"
        ).add_field(
            name="Uptime:",
            value=f"{humandelta(datetime.now() - self.bot.start_time)} (since {humandate(self.bot.start_time)})"
        ).set_footer(
            text=f"requested by {ctx.message.author}",
            icon_url=ctx.message.author.avatar_url
        )
        await ctx.send(embed=embed)

    @commands.command()
    async def ping(self, ctx: commands.Context):
        """Check if the bot is alive and return its latency."""
        await ctx.send(f"Pong! :ping_pong: ({self.bot.latency*1000:.2f}ms)")

    @commands.command()
    async def invite(self, ctx: commands.Context, guild: discord.Guild = None):
        """Get the invite link of the bot to be able to invite it.

        Sends you the invite link in DMs.
        """
        app = await self.bot.application_info()
        url = discord.utils.oauth_url(app.id, discord.Permissions(2046684374), guild)
        await ctx.send(f"Invite me by clicking here: {url}")
    
    @commands.command(aliases=['prefixes'])
    async def prefix(self, ctx: commands.Context, *prefixes: str):
        """Get or set the prefix for the current guild"""
        if prefixes:
            if ctx.guild is None:
                raise commands.NoPrivateMessage("You cannot set prefixes outside a server")
            if not ctx.channel.permissions_for(ctx.author).manage_guild: # type: ignore
                raise commands.MissingPermissions(['manage_guild'])
            prev = await self.bot.set_guild_prefix(ctx.guild, list(prefixes))
            f = ', '.join(f"`{prefix}`" for prefix in prev)
            t = ', '.join(f"`{prefix}`" for prefix in prefixes)
            await ctx.send(f"Changed prefixes from {f} to {t}")
        else:
            p = ', '.join(f"`{prefix}`" for prefix in await self.bot.get_guild_prefix(ctx.guild))
            await ctx.send(f'Prefixes for {ctx.guild}: {p}')

def setup(bot):
    bot.add_cog(General(bot))
