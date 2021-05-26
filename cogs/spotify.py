import aiohttp
import discord
from config import config, logger
from discord import Emoji, PartialEmoji, Role
from discord.ext import commands
from discord.ext.commands import Bot, Context

class Spotify(commands.Cog, name="spotify"):
    """Shows what the owner is listening to on spotify"""

    def __init__(self, bot: Bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()

def setup(bot):
    bot.add_cog(Spotify(bot))
