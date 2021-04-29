import os
import random
from typing import List

import discord
from config import config, logger
from discord import TextChannel
from discord.ext import commands
from discord.ext.commands import Bot, Context


class Memes(commands.Cog, name="memes"):
    """A utility cog for reposting memes."""
    memebin: TextChannel
    _memes: List[str] = []

    def __init__(self, bot: Bot):
        self.bot = bot
        self.meme_folder = config['memes']['meme_folder']
        self.running_on_sever = not os.path.isdir(self.meme_folder)

    @commands.Cog.listener()
    async def on_ready(self):
        channel = config['memes'].getint('memebin_channel')
        self.memebin = await self.bot.fetch_channel(channel)
        self._memes = [msg.attachments[0].url for msg in await self.memebin.history(limit=None).flatten()]

    @commands.command('meme', aliases=['randommeme', 'memes'], invoke_without_command=True)
    async def meme(self, ctx: Context):
        """Sends a random meme from the owner's meme folder.

        All memes are gotten from a meme bin channel.
        """
        if self._memes:
            logger.debug(f'Sending meme to {ctx.guild}/{ctx.channel}')
            await ctx.send(random.choice(self._memes))
        else:
            await ctx.send('https://tenor.com/view/loading-discord-loading-discord-boxes-squares-gif-16187521')

    @commands.command('repost', aliases=['memerepost', 'repostmeme'])
    async def repost(self, ctx: Context, channel: TextChannel = None):
        """Reposts a random meme from meme channels in the server

        Looks thorugh the last 100 messages in every channel with meme in its name
        and then posts it in the current channel. You can specify which channel to repost from.
        """
        if channel is None:
            channels = [
                channel for channel in ctx.guild.text_channels if 'meme' in channel.name]
            if not channels:
                ctx.send(
                    'No meme channels found, make sure this bot can see them.')
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

    @commands.command('update_memebin', hidden=True)
    @commands.is_owner()
    async def update_memebin(self, ctx: Context):
        """Dumps all memes from the owner's meme folder into a memebin.

        This can only be used by the owner. The uploaded memes will not be sorted.
        """
        if self.running_on_sever:
            return

        logger.info('Updating memebin!')

        memes = set(os.listdir(self.meme_folder))
        await ctx.send(f'Found {len(memes)} memes in your folder. Now filtering unwanted memes...')

        uploaded = set()
        todelete = []
        async for msg in self.memebin.history(limit=None):
            if len(msg.attachments) != 1:
                todelete.append(msg)  # normal message
                continue

            file = msg.attachments[0]
            if file.filename not in memes:
                todelete.append(msg)  # unwanted meme
                continue
            if file.filename in uploaded:
                todelete.append(msg)  # repost
                continue

            uploaded.add(file.filename)

        toupload = memes - uploaded

        await ctx.send(f'Found {len(uploaded)} uploaded memes, '
                       f'that means {len(toupload)} memes will be uploaded and {len(todelete)} will be deleted.\n'
                       f'Proceed? [y/n]')
        response = await self.bot.wait_for('message', check=lambda msg: msg.author == ctx.author)
        if response.content.lower() != 'y':
            await ctx.send('Aborted!')
            return

        await ctx.send(f'Deleting {len(todelete)} messages...')
        for msg in todelete:
            await msg.delete()

        await ctx.send(f'Uploading {len(toupload)} memes...')
        for file in toupload:
            try:
                with open(os.path.join(self.meme_folder, file), 'rb') as fp:
                    msg = await self.memebin.send(file=discord.File(fp, file))
                    self._memes.append(msg.attachments[0].url)
            except discord.HTTPException as e:
                if e.status == 413:
                    await ctx.send(f'Cannot upload `{file}`: Too large')
                else:
                    await ctx.send(f'Unexpected error when uploading `{file}`: {e}')

        await ctx.send(f'{ctx.author.mention} Finished sending memes!')

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
