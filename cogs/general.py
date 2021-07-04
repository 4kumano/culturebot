import time
from datetime import datetime

import discord
from discord import Guild
from discord.ext import commands
from discord.ext.commands import Context
from utils import CCog, humandate, humandelta

start_time = time.time()

class General(CCog, name="general"):
    """General all-purpose commands every bot has"""
    
    @commands.command("info", aliases=["botinfo"])
    async def info(self, ctx: Context):
        """Basic info about the bot.

        Stuff like the author.
        """
        app = await self.bot.application_info()
        embed = discord.Embed(
            title="Culture bot.",
            description=f"A multi-purpose bot made by {app.owner}, contains random features I decided to add on a whim.\n"
                        "This bot is made to not have any databases, meaning every user and guld is anonymous to it.",
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

    @commands.command(name="ping")
    async def ping(self, ctx: Context):
        """Check if the bot is alive and return its latency."""
        await ctx.send(f"Pong! :ping_pong: ({self.bot.latency*1000:.2f}ms)")

    @commands.command(name="invite")
    async def invite(self, ctx: Context, guild: Guild = None):
        """Get the invite link of the bot to be able to invite it.

        Sends you the invite link in DMs.
        """
        app = await self.bot.application_info()
        url = discord.utils.oauth_url(app.id, discord.Permissions(2046684374), guild)
        await ctx.send(f"Invite me by clicking here: {url}")
    
    @commands.command()
    async def prefix(self, ctx: Context, prefix: str = None):
        """Set the prefix for the current guild"""
        if prefix:
            if ctx.guild is None:
                raise commands.NoPrivateMessage("You cannot set prefixes outside a server")
            if not ctx.channel.permissions_for(ctx.author).manage_guild: # type: ignore
                raise commands.MissingPermissions(['manage_guild'])
            await ctx.send("This bot doesn't have a database, how do you expect me to change a prefix :neutral_face: ")
            return
        prefixes = ', '.join(f"`{prefix}`" for prefix in await self.bot.get_guild_prefix(ctx.guild))
        await ctx.send(f'Prefixes for {ctx.guild}: {prefixes}')

def setup(bot):
    bot.add_cog(General(bot))
