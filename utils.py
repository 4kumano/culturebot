from __future__ import annotations

import asyncio
from asyncio.events import AbstractEventLoop
import configparser
import inspect
import re
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from functools import partial
from logging import Logger
from typing import (Any, Callable, Coroutine, Iterable, Mapping, Optional, TYPE_CHECKING,
                    TypeVar, Union)

import discord
from discord import Member, Message, NotFound, User
from discord.abc import Messageable
from discord.embeds import Embed
from discord.ext import commands
from discord.ext.commands import Bot, Context

from config import config, logger
if TYPE_CHECKING:
    import bot as _bot

T = TypeVar('T')

class CCog(commands.Cog):
    """A command with a config"""
    __cog_name__: str # discord.py-stubs does not define this???
    bot: '_bot.CBot'
    config: configparser.SectionProxy
    logger: Logger = logger
    
    def __init__(self, bot: '_bot.CBot') -> None:
        pass
    
    async def init(self) -> None:
        """Runs after __init__ as a task"""
    
    def __new__(cls, *args, **kwargs):
        cls.bot = args[0]
        
        self: CCog = super().__new__(cls, *args, **kwargs)
        
        self.__cog_name__ = self.__cog_name__.lower()
        if self.__cog_name__ in config:
            self.config = config[self.__cog_name__]
        
        if not inspect.iscoroutinefunction(self.init):
            self.bot.loop.run_in_executor(None, self.init)
        else:
            self.bot.loop.create_task(self.init())
        
        return self

def wrap(*string: str, lang: str = '') -> str:
    """Wraps a string in codeblocks."""
    return f'```{lang}\n' + ''.join(string) + '\n```'

def multiline_join(strings: list[str], sep: str = '', prefix: str = '', suffix: str = '') -> str:
    """Like str.join but multiline."""
    parts = zip(*(str(i).splitlines() for i in strings))
    return '\n'.join(prefix+sep.join(i)+suffix for i in parts)

def chunkify(string: Union[str, Iterable[str]], max_size: int = 1980, newlines: bool = True, wrapped: bool = False) -> list[str]:
    """Takes in a string or a list of lines and splits it into chunks that fit into a single discord message
    
    You may change the max_size to make this function work for embeds.
    There is a 20 character leniency given to max_size by default.
    
    If newlines is true the chunks are formatted with respect to newlines as long as that's possible.
    If wrap is true the chunks will be individually wrapped in codeblocks.
    """
    if newlines:
        string = string.split('\n') if isinstance(string, str) else string
        
        chunks = ['']
        for i in string:
            i += '\n'
            if len(chunks[-1]) + len(i) < max_size:
                chunks[-1] += i
            elif len(i) > max_size:
                # we don't wrap here because the wrapping will be done no matter what
                chunks.extend(chunkify(i, max_size, newlines=False, wrapped=False))
            else:
                chunks.append(i)
    else:
        string = string if isinstance(string, str) else '\n'.join(string)
        chunks = [string[i:i+max_size] for i in range(0, len(string), max_size)]
    
    if wrapped:
        chunks = [wrap(i) for i in chunks]
   
    return chunks

async def send_chunks(destination: Messageable, string: str, wrapped: bool = False) -> list[Message]:
    """Sends a long string to a channel"""
    return [await destination.send(chunk) for chunk in chunkify(string, wrapped=wrapped)]

def humandate(dt: Optional[datetime]) -> str:
    if dt is None:
        return 'unknown'
    return dt.strftime("%a, %b %d, %Y %H:%M %p")

def utc_as_timezone(dt: datetime, naive: bool = False, reverse: bool = False) -> datetime:
    """Converts a random utc datetime into a correct local timezone aware datetime"""
    ts = dt.timestamp()
    localtm = time.localtime(ts)
    delta = timedelta(seconds=localtm.tm_gmtoff)
    if reverse:
        delta = -delta
    
    tz = timezone(delta, localtm.tm_zone)
    
    dt += delta
    return dt if naive else dt.astimezone(tz)


async def report_bug(ctx: Context, error: Exception):
    """Reports a bug to a channel"""
    channel_id = config['bot'].getint('bugreport')
    channel = ctx.bot.get_channel(channel_id) or await ctx.bot.fetch_channel(channel_id)
    assert isinstance(channel, discord.TextChannel)

    tb = traceback.format_exception(type(error), error, error.__traceback__)
    
    embed = discord.Embed(
        color=discord.Colour.red(),
        title=type(error).__name__,
        url=ctx.message.jump_url,
        timestamp=datetime.now()
    ).set_author(
        name=str(ctx.author),
        icon_url=ctx.author.avatar_url
    )
    for chunk in chunkify(tb, 1000, wrapped=True):
        embed.add_field(
            name='\u200b​',
            value=chunk,
            inline=False
        )
    
    await channel.send(embed=embed)

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
    
    if str(reaction) == yes:
        await message.remove_reaction(no, bot.user)
        return True
    else:
        await message.clear_reactions()
        return False

async def discord_choice(
    bot: Bot, message: Message, user: Union[User, Member],
    choices: Union[Mapping[str, T], list[T]],
    timeout: float = 60, delete_after_timeout: bool = True,
    cancel: Optional[str] = '❌'
) -> Optional[T]:
    """Creates a discord reaction choice

    Takes in a bot to wait with, a message to add reactions to and a user to wait for.
    Choices must either be a dict of emojis to choices or an iterable of emojis.
    If the items of iterable have a `value` attribute that will be the emoji.

    If cancel is set to None, the user will not be able to cancel.
    """
    if isinstance(choices, Mapping):
        reactions = choices
    else:
        # possible enums should be accounted for
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
        await message.delete()
        return None

    return reactions[str(reaction)]

def error_embed(description: str = None) -> Embed:
    embed = discord.Embed(
        colour=discord.Colour.red(),
        title="An error was encountered",
        description=description,
        timestamp=datetime.now()
    )
    return embed

async_executor = ThreadPoolExecutor()
def asyncify(func: Callable[..., T]) -> Callable[..., Coroutine[Any, Any, T]]:
    """Turn a normal function into a coroutine. 
    We don't use an awaitable because of type restrictions in dpy"""
    loop = asyncio.get_event_loop()
    async def wrapper(*args, **kwargs):
        return await loop.run_in_executor(async_executor, partial(func, *args, **kwargs))
    return wrapper

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
