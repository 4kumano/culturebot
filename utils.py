from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import asyncio
from typing import Optional, TypeVar, Union
import os

from discord import Message, User
from discord.ext.commands import Bot

T = TypeVar('T')


def multiline_join(strings: list[str], sep: str = '', prefix: str = '', suffix: str = '') -> str:
    """Like str.join but multiline."""
    parts = zip(*(str(i).splitlines() for i in strings))
    return '\n'.join(prefix+sep.join(i)+suffix for i in parts)


async def discord_choice(
    bot: Bot, message: Message, user: User,
    choices: Union[dict[str, T], list[T]],
    timeout: float = 60, delete_after_timeout: bool = True,
    cancel: Optional[str] = '❌'
) -> Optional[T]:
    """Creates a discord reaction choice

    Takes in a bot to wait with, a message to add reactions to and a user to wait for.
    Choices must either be a dict of emojis to choices or an iterable of emojis.
    If the items of iterable have a `value` attribute that will be the emoji.

    If cancel is set to None, the user will not be able to cancel.
    """
    if isinstance(choices, dict):
        reactions = choices.copy()
    else:
        reactions = {getattr(i, 'value', str(i)).strip(): i for i in choices}

    for i in reactions:
        await message.add_reaction(i)
    if cancel:
        await message.add_reaction(cancel)

    try:
        reaction, _ = await bot.wait_for(
            'reaction_add',
            check=lambda r, u: (str(r) in reactions or str(r) == cancel) and u == user,
            timeout=timeout
        )
    except asyncio.TimeoutError:
        if delete_after_timeout:
            await message.delete()
        return None
    finally:
        await message.clear_reactions()

    if str(reaction) == cancel:
        if delete_after_timeout:
            await message.delete()
        return None

    return reactions[str(reaction)]


def wrap(*string: str, lang: str = '') -> str:
    """Wraps a string in codeblocks."""
    return f'```{lang}\n' + ''.join(string) + '\n```'

class PyDrive:
    """Manages drive actions through a simple api"""
    def __init__(self, settings_file: str = 'pydrive_settings.yaml', directory: str = 'memebin'):
        """Authenticates and connects to drive."""
        from pydrive.auth import GoogleAuth
        from pydrive.drive import GoogleDrive
        
        gauth = GoogleAuth(settings_file)
        gauth.LocalWebserverAuth()
        self.drive = GoogleDrive(gauth)
        
        self.directory = self._get_directory(directory)
    
    def _get_directory(self, directory: str):
        """Returns a directory with the same name"""
        for i in self.listdir('root'):
            if i['title'] == directory:
                return i
        
        file = self.drive.CreateFile({'title' : directory, 'mimeType' : 'application/vnd.google-apps.folder'})
        file.Upload()
        return file
    
    @staticmethod
    def _get_parents(*directories):
        """Gets parents from directories."""
        return [{'id': i['id']} for i in directories]

    def upload(self, path: str, filename: str = None, update: bool = True):
        """Uploads a file"""
        # default to None when not updating
        file = self.find_file(filename) if update else None
        
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
    
    
    def listdir(self, directory_id: str = None):
        """Lists all files in a directory. By default lists the defaut directory."""
        directory_id = directory_id or self.directory['id']
        return self.drive.ListFile({'q': f"'{directory_id}' in parents and trashed=false"}).GetList()
    
    def find_file(self, filename: str, directory_id: str = None):
        """Finds a file in a directory"""
        for i in self.listdir(directory_id):
            if i['title'] == filename:
                return i
        return None
    
    def upload_directory(self, directory: str):
        """Uploads the entire directory"""
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
            
            for i,future in enumerate(futures, 1):
                future.result()
                print(i)

        print(f'Uploaded {len(files)} files')

if __name__ == '__main__':
    drive = PyDrive()
    drive.upload_directory('C:/Users/D/Memes')
