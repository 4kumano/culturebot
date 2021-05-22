from __future__ import annotations
import argparse

import asyncio
import shlex
from typing import Callable, List, Optional, TypeVar, Union

from discord import Message, User
from discord.ext import commands
from discord.ext.commands import Bot
from discord.member import Member

T = TypeVar('T')


def multiline_join(strings: list[str], sep: str = '', prefix: str = '', suffix: str = '') -> str:
    """Like str.join but multiline."""
    parts = zip(*(str(i).splitlines() for i in strings))
    return '\n'.join(prefix+sep.join(i)+suffix for i in parts)

def chunkify(string: str, max_size: int = 1950) -> list[str]:
    """Takes in a string and splits it into chunks that fit into a single discord message
    
    You may change the max_size to make this function work for embeds.
    There is a 50 character leniency given to max_size by default.
    """
    return [string[i:i+max_size] for i in range(0, len(string), max_size)]

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
        await message.clear_reactions()

    if str(reaction) == cancel:
        if delete_after_timeout:
            await message.delete()
        return None

    return reactions[str(reaction)]


def wrap(*string: str, lang: str = '') -> str:
    """Wraps a string in codeblocks."""
    return f'```{lang}\n' + ''.join(string) + '\n```'

class DiscordArgparse(commands.Converter, argparse.Namespace):
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
        setattr(cls, 'parser', parser) # ensure linters don't expect a parser argument
        return commands.Greedy[cls]

    async def convert(self, ctx, argument: str) -> argparse.Namespace:
        try:
            args, argv = self.parser.parse_known_args(shlex.split(argument))
        except argparse.ArgumentError as e:
            raise commands.BadArgument(f'Could not parse arguments: {e.message}')
        if argv:
            raise commands.TooManyArguments(
                f'Recieved {len(argv)} extra arguments: {", ".join(argv)}\n' 
                + self.parser.format_usage()
            )
        return args
