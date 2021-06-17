import time

import discord
from discord import Forbidden
from discord.ext import commands
from discord.ext.commands import Bot, Context
from utils import CCog, config

start_time = time.time()

class General(CCog, name="general"):
    """General all-purpose commands every bot has"""
    
    @commands.command("info", aliases=["botinfo"])
    async def info(self, ctx: Context):
        """Basic info about the bot.

        Stuff like the author.
        """
        embed = discord.Embed(
            title="Culture bot.",
            description="A multi-purpose bot made by sadru#1323, contains random features I decided to add on a whim.\n"
                        "This bot is made to not have any databases, meaning every user and guld is anonymous to it.",
            color=0x42F56C
        ).set_thumbnail(
            url=self.bot.user.avatar_url
        ).add_field(
            name="Owner:",
            value="sadru#1323"
        ).add_field(
            name="Prefix:",
            value=config['bot']['prefix']
        ).add_field(
            name="Made with:",
            value="Python"
        ).add_field(
            name="Uptime:",
            value=time.time() - start_time
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
    async def invite(self, ctx: Context):
        """Get the invite link of the bot to be able to invite it.

        Sends you the invite link in DMs.
        """
        app = await self.bot.application_info()
        url = discord.utils.oauth_url(app.id, discord.Permissions(administrator=True), )
        await ctx.send(f"Invite me by clicking here: {url}")
            

def setup(bot):
    bot.add_cog(General(bot))
