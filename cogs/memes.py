import random
from typing import List

import aiohttp
import discord
from config import config, logger
from discord import TextChannel, File
from discord.ext import commands, tasks
from discord.ext.commands import Bot, Context
from pydrive.files import GoogleDriveFile

from utils import PyDrive

class Memes(commands.Cog, name="memes"):
    """A utility cog for reposting memes."""
    _memes: List[GoogleDriveFile] = []
        
    def __init__(self, bot: Bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()

    @commands.Cog.listener()
    async def on_ready(self):
        self.drive = PyDrive(directory=config['memes']['folder'])
        self.update_memes.start()
    
    def cog_unload(self):
        self.update_memes.cancel()
        if not self.session.closed:
            self.bot.loop.create_task(self.session.close())
    
    @tasks.loop(hours=6)
    async def update_memes(self):
        """Updates the meme files"""
        self._memes = [i for i in self.drive.listdir() if i['downloadUrl']]
        random.shuffle(self._memes)
    
    async def _get_meme(self, file: GoogleDriveFile) -> File:
        """Gets a discord file object from a pydrive file object"""
        if file.content is None:
            file.FetchContent()
        
        return File(file.content, file['title'])

    @commands.command('meme', aliases=['randommeme', 'memes'], invoke_without_command=True)
    async def meme(self, ctx: Context):
        """Sends a random meme from the owner's meme folder.

        All memes are gotten from a meme bin channel.
        """
        logger.debug(f'Sending meme to {ctx.guild}/{ctx.channel}')
        await ctx.trigger_typing()
        file = await self._get_meme(random.choice(self._memes))
        await ctx.send(file=file)

    @commands.command('repost', aliases=['memerepost', 'repostmeme'])
    async def repost(self, ctx: Context, channel: TextChannel = None):
        """Reposts a random meme from meme channels in the server

        Looks thorugh the last 100 messages in every channel with meme in its name
        and then posts it in the current channel. You can specify which channel to repost from.
        """
        if channel is None:
            channels = [channel for channel in ctx.guild.text_channels 
                        if 'meme' in channel.name]
            if not channels:
                ctx.send('No meme channels found, make sure this bot can see them.')
                return

            channel = random.choice(channels)

        logger.debug(
            f'Reposting meme from {channel.guild}/{channel} to {ctx.guild}/{ctx.channel}')
        memes = []
        async for msg in channel.history():
            memes += [i.url for i in msg.attachments]
            memes += [i.url for i in msg.embeds if i is not discord.Embed.Empty]
        if not memes:
            await ctx.send(f'Channel {channel.mention} does not have any memes.')
            return

        await ctx.send(random.choice(memes))

    @commands.command('dump_memes', hidden=True)
    @commands.is_owner()
    async def dump_memes(self, ctx: Context, channel: TextChannel = None):
        """Dumps all memes from the memebin into a channel.

        This can only be used by the owner.
        """
        channel = channel or ctx.channel
        async for msg in self.memebin.history(limit=None):
            await channel.send(msg.attachments[0].url)


def setup(bot):
    bot.add_cog(Memes(bot))
