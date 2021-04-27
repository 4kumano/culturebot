import platform

import discord
from discord import Forbidden
from discord.ext import commands
from discord.ext.commands import Bot, Context

from config import config


class General(commands.Cog, name="general"):
    """General all-purpose commands every bot has"""
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.command("info", aliases=["botinfo"])
    async def info(self, ctx: Context):
        """Basic info about the bot.
        
        Stuff like the author.
        """
        embed = discord.Embed(
            title="Culture bot.",
            description="A multi-purpose bot made sadru#1323, contains random features I decided to add on a whim.",
            color=0x42F56C
        )
        embed.set_thumbnail(url=self.bot.user.avatar_url)
        embed.add_field(
            name="Owner:",
            value="sadru#1323"
        )
        embed.add_field(
            name="Prefix:",
            value=config['bot']['prefix']
        )
        embed.add_field(
            name="Made with:",
            value=f"Python {platform.python_version()}"
        )
        embed.set_footer(
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
        try:
            await ctx.author.send(f"Invite me by clicking here: https://discordapp.com/oauth2/authorize?&client_id={app.id}&scope=bot&permissions=8")
        except Forbidden:
            await ctx.send('Could not invite you, you have disabled direct messages.')
        else:
            await ctx.send("I sent you a private message!")
    
    @commands.command('purge')
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx: Context, amount: int):
        await ctx.channel.purge(limit=amount)

def setup(bot):
    bot.add_cog(General(bot))
