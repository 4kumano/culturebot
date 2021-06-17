import io
import os
import random
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional

import aiohttp
import discord
from discord import File, TextChannel
from discord.ext import commands, tasks
from discord.ext.commands import Bot, Context
from pydrive.auth import GoogleAuth, LoadAuth, RefreshError
from pydrive.drive import GoogleDrive
from pydrive.files import ApiRequestError, GoogleDriveFile
from utils import CCog, asyncify


class PyDrive:
    """Manages drive actions through a simple api"""
    def __init__(self, settings_file: str = 'pydrive_settings.yaml', directory: str = 'memebin'):
        """Authenticates and connects to drive."""
        auth = GoogleAuth(settings_file)
        auth.LocalWebserverAuth()
        self.drive = GoogleDrive(auth)
        self.directory = self._get_directory(directory)

    def _get_directory(self, directory: str) -> GoogleDriveFile:
        """Returns a directory with the same name"""
        for i in self.listdir('root'):
            if i['title'] == directory:
                return i

        file = self.drive.CreateFile()
        file['title'] = directory
        file['mimeType'] = 'application/vnd.google-apps.folder'
        file.Upload()
        return file

    @staticmethod
    def _get_parents(*directories: GoogleDriveFile) -> List[dict]:
        """Gets parents from directories."""
        return [{'id': i['id']} for i in directories]

    def upload(self, path: str, filename: str = None) -> GoogleDriveFile:
        """Uploads a file"""
        # default to None when not updating
        file = self.find_file(filename) if filename else None

        if file is None:
            file = self.drive.CreateFile()
            file['title'] = filename or os.path.split(path)[1]
            file['parents'] = self._get_parents(self.directory)

        file.SetContentFile(path)
        file.Upload()
        return file

    def delete(self, filename: str, trash: bool = False) -> bool:
        """Deletes a file. Returns whether succeeded."""
        file = self.find_file(filename)
        if file is None:
            return False
        if trash:
            file.Trash()
        else:
            file.Delete()
        return True

    def listdir(self, directory_id: str = None) -> List[GoogleDriveFile]:
        """Lists all files in a directory. By default lists the default directory."""
        directory_id = directory_id or self.directory['id']
        return self.drive.ListFile({'q': f"'{directory_id}' in parents and trashed=false"}).GetList()

    def find_file(self, filename: str, directory_id: str = None) -> Optional[GoogleDriveFile]:
        """Finds a file in a directory"""
        for i in self.listdir(directory_id):
            if i['title'] == filename:
                return i
        return None

    def upload_directory(self, directory: str):
        """Uploads an entire directory to google drive"""
        files = set(os.listdir(directory))
        print(f"Found {len(files)} files in {directory}.")

        uploaded = set()
        todelete = []
        for file in self.listdir():
            if file['title'] not in files:
                todelete.append(file)  # unwanted file
                continue
            if file['title'] in uploaded:
                todelete.append(file)  # duplicate file
                continue

            uploaded.add(file['title'])

        toupload = files - uploaded

        print(f'Found {len(uploaded)} uploaded files, '
              f'that means {len(toupload)} files will be uploaded and {len(todelete)} will be deleted.\n'
              f'Proceed? [y/n]')
        if input() != 'y':
            print('Aborted!')
            return

        print(f'Deleting {len(todelete)} files...')
        for file in todelete:
            print(file)
            file.Delete()

        print(f'Uploading {len(toupload)} files...')

        with ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(self.upload, os.path.join(directory, file))
                for file in toupload
            ]

            for i, future in enumerate(futures, 1):
                future.result()
                print(i)

        print(f'Uploaded {len(files)} files')

@asyncify
@LoadAuth
def _download_file(file: GoogleDriveFile, spoiler: bool = False) -> Optional[File]:
    """Downloads a pydrive file object and returns a discord file object"""
    try:
        content = io.BytesIO(file._DownloadFromUrl(file['downloadUrl']))
    except ApiRequestError:
        return None
    return File(content, file['title'], spoiler=spoiler)

class Memes(CCog, name="memes"):
    """A utility cog for reposting memes."""
    _memes: List[GoogleDriveFile] = []

    async def init(self):
        self.drive = PyDrive(self.config['pydrive_settings'], self.config['folder'])
        self.update_memes.start()

    def cog_unload(self):
        self.update_memes.cancel()
        if not self.bot.session.closed:
            self.bot.loop.create_task(self.bot.session.close())

    @tasks.loop(hours=6)
    @asyncify
    def update_memes(self):
        """Updates the meme files"""
        self._memes = [i for i in self.drive.listdir() 
                       if i['downloadUrl'] and int(i['fileSize']) < 0x100000]
        random.shuffle(self._memes)

    @commands.command('meme', aliases=['randommeme'])
    @commands.cooldown(2, 1, commands.BucketType.channel)
    async def meme(self, ctx: Context):
        """Sends a random meme from the owner's meme folder.

        Make take up to 1s to upload the file when the bot 
        is configured to upload directly instead of sending links.
        
        If an amount is set then the bot sends that many memes, max is 10.
        """
        await ctx.trigger_typing()
        file = await _download_file(random.choice(self._memes))
        if file is None:
            raise commands.CommandError("There are too many memes being requested right now, please wait a second")
        await ctx.send(file=file)

    @commands.command('repost', aliases=['memerepost', 'repostmeme'])
    async def repost(self, ctx: Context, channel: TextChannel = None):
        """Reposts a random meme from meme channels in the server

        Looks thorugh the last 100 messages in every channel with meme in its name
        and then reposts a random meme from them in the current channel. 
        You can specify which channel to repost from.
        """
        if channel is None:
            channels = [channel for channel in ctx.guild.text_channels
                        if 'meme' in channel.name]
            if not channels:
                await ctx.send('No meme channels found, make sure this bot can see them.')
                return

            channel = random.choice(channels)

        self.logger.debug(f'Reposting meme from {channel} to {ctx.channel}')
        memes = []
        async for msg in channel.history():
            memes += [i.url for i in msg.attachments]
            memes += [i.url for i in msg.embeds if i.url]
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
        channel = channel or ctx.channel # type: ignore
        path = self.config['localdir']
        for file in os.listdir(path):
            try:
                await channel.send(file=File(os.path.join(path, file), file))
            except discord.HTTPException:
                pass


def setup(bot):
    try:
        bot.add_cog(Memes(bot))
    except RefreshError as e:
        Memes.logger.error(e)


if __name__ == '__main__':
    from utils import config
    drive = PyDrive(config['memes']['pydrive_settings'], config['memes']['folder'])
    drive.upload_directory(config['memes']['localdir'])
