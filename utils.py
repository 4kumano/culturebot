from __future__ import annotations

import argparse
import asyncio
import configparser
import re
import shlex
from functools import partial
from typing import Optional, TypeVar, Union

import discord
from discord import Member, Message, NotFound, User
from discord.ext import commands
from discord.ext.commands import Bot, Context

from config import config

T = TypeVar('T')

class CCog(commands.Cog):
    """A command with a config"""
    config: configparser.SectionProxy
    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls, *args, **kwargs)
        if self.__cog_name__ in config:
            self.config = config[self.__cog_name__]
        return self

def multiline_join(strings: list[str], sep: str = '', prefix: str = '', suffix: str = '') -> str:
    """Like str.join but multiline."""
    parts = zip(*(str(i).splitlines() for i in strings))
    return '\n'.join(prefix+sep.join(i)+suffix for i in parts)

def chunkify(string: str, max_size: int = 1980, newlines: bool = False, wrapped: bool = False) -> list[str]:
    """Takes in a string and splits it into chunks that fit into a single discord message
    
    You may change the max_size to make this function work for embeds.
    There is a 20 character leniency given to max_size by default.
    
    If newlines is true the chunks are formatted with respect to newlines as long as that's possible.
    If wrap is true the chunks will be individually wrapped in codeblocks.
    """
    if newlines:
        chunks = ['']
        for i in string.split('\n'): # keep whitespace
            i += '\n'
            if len(chunks[-1]) + len(i) < max_size:
                chunks[-1] += i
            elif len(i) > max_size:
                # we don't wrap here because the wrapping will be done no matter what
                chunks.extend(chunkify(i, max_size, newlines=False, wrapped=False))
            else:
                chunks.append(i)
    else:
        chunks = [string[i:i+max_size] for i in range(0, len(string), max_size)]
    
    if wrapped:
        return [wrap(i) for i in chunks]
    else:
        return chunks

async def discord_choice(
    bot: Bot, message: Message, user: Union[User, Member],
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
        try:
            await message.clear_reactions()
        except NotFound:
            return None

    if str(reaction) == cancel:
        if delete_after_timeout:
            await message.delete()
        return None

    return reactions[str(reaction)]

def bot_channel_only(regex: str = r'bot|spam', category: bool = True, dms: bool = True):
    def predicate(ctx: Context):
        channel = ctx.channel
        if not isinstance(channel, discord.TextChannel):
            if dms:
                return True
            raise commands.CheckFailure('Dms are not counted as a bot channel.')

        if re.search(regex, channel.name) or category and re.search(regex, str(channel.category)):
            return True

        raise commands.CheckFailure('This channel is not a bot channel.')

    return commands.check(predicate)

async def confirm(bot: Bot, message: Message, user: Union[User, Member], timeout: int = 15) -> bool:
    """Confirms a message"""
    yes, no = '✅', '❌'
    await message.add_reaction(yes)
    await message.add_reaction(no)
    try:
        reaction, _ = await bot.wait_for(
            'reaction_add',
            check=lambda r, u: str(r) in (yes, no) and u == user,
            timeout=timeout
        )
    except asyncio.TimeoutError:
        return False
    
    return str(reaction) == yes
    

def wrap(*string: str, lang: str = '') -> str:
    """Wraps a string in codeblocks."""
    return f'```{lang}\n' + ''.join(string) + '\n```'

class DiscordArgparse(argparse.Namespace):
    """An argument parser for discord.py build in argparse
    
    As oposed to using normal argparse as an annotation,
    using DiscordArgparse ensures the typing is correct by inheriting from Namespace.
    
    Usage:
    ```
    parser = argparse.ArgumentParser()
    parser.add_argument('--foo', type=int)
    parser.add_argument('-x', action='store_true')
    
    @bot.command()
    async def command(ctx, args: DiscordArgparse[parser]):
        print(args.foo, args.x)
    ```
    
    When an error is encountered during parsing a BadArgument Exception is raised with a custom message.
    """
    def __class_getitem__(cls, parser: argparse.ArgumentParser):
        """Initialize the converter with an ArgumentParser"""
        parser.exit_on_error = False # type: ignore
        return partial(cls.convert, parser)
    
    @staticmethod
    def convert(parser: argparse.ArgumentParser, argument: str) -> argparse.Namespace:
        try:
            args, argv = parser.parse_known_args(shlex.split(argument))
        except argparse.ArgumentError as e:
            raise commands.BadArgument(f'Could not parse arguments: {e.message}')
        if argv:
            raise commands.TooManyArguments(
                f'Recieved {len(argv)} extra arguments: {", ".join(argv)}\n' 
                + parser.format_usage()
            )
        return args
