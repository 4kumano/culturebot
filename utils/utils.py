from __future__ import annotations

import asyncio
import re
import time
from asyncio.tasks import ALL_COMPLETED, FIRST_COMPLETED, Task
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from functools import partial
from itertools import repeat
from typing import *  # type: ignore

from typing_extensions import TypeAlias
if TYPE_CHECKING: # 3.10 is not out yet techincally
    from typing_extensions import ParamSpec
else:
    ParamSpec = lambda *_,**__: None

import discord
from discord import Member, Reaction, User
from discord.ext import commands
from discord.ext.commands import Bot, Context

T = TypeVar("T")
T1 = TypeVar("T1")
T2 = TypeVar("T2")
P = ParamSpec("P")

_Event: TypeAlias = Union[str, tuple[str, Optional[Callable[..., bool]]]]

def humandate(dt: Optional[datetime]) -> str:
    if dt is None:
        return "unknown"
    return dt.strftime("%a, %b %d, %Y %H:%M %p")

def humandelta(delta: timedelta) -> str:
    s = int(delta.total_seconds())
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)

    return (f"{d}d" if d else "") + (f"{h}h" if h else "") + f"{m}min {s}s"

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

async_executor = ThreadPoolExecutor()
def asyncify(func: Callable[P, T]) -> Callable[P, Coroutine[Any, Any, T]]:
    """Turn a normal function into a coroutine.
    We don't use an awaitable because of type restrictions in dpy"""
    loop = asyncio.get_event_loop()

    async def wrapper(*args, **kwargs):
        return await loop.run_in_executor(async_executor, partial(func, *args, **kwargs))

    return wrapper

def bot_channel_only(regex: str = r"bot|spam", category: bool = True, dms: bool = True):
    def predicate(ctx: Context):
        channel = ctx.channel
        if not isinstance(channel, discord.TextChannel):
            if dms:
                return True
            raise commands.CheckFailure("Dms are not counted as a bot channel.")

        if re.search(regex, channel.name) or category and re.search(regex, str(channel.category)):
            return True

        raise commands.CheckFailure("This channel is not a bot channel.")

    return commands.check(predicate)


def repeat_once(first: T1, rest: T2 = '\u200b') -> Iterator[Union[T1, T2]]:
    yield first
    yield from repeat(rest)

def zip_once(iterable: Iterable[T], first: T1, rest: T2 = '\u200b') -> Iterator[tuple[T, Union[T1, T2]]]:
    yield from zip(iterable, repeat_once(first, rest))


async def _wait_for_many(
    bot: Bot,
    events: Iterable[_Event],
    timeout: Optional[int] = None,
    return_when: str = ALL_COMPLETED,
) -> set[Task[Any]]:
    """Waits for multiple events"""
    events = [(e, None) if isinstance(e, str) else (e[0], e[1]) for e in events]
    futures = [
        bot.loop.create_task(bot.wait_for(event, check=check), name=event) 
        for event, check in events
    ]
    done, pending = await asyncio.wait(futures, loop=bot.loop, timeout=timeout, return_when=return_when)
    for task in pending:
        task.cancel()
    return done

async def wait_for_any(bot: Bot, *events: _Event, timeout: int = None) -> Union[tuple[str, Any], tuple[Literal[''], None]]:
    """Waits for the first event to complete"""
    tasks = await _wait_for_many(bot, events, timeout=timeout, return_when=FIRST_COMPLETED)
    if not tasks:
        return '', None
    task = tasks.pop()
    return task.get_name(), await task

async def wait_for_all(bot: Bot, *events: _Event, timeout: int = None) -> dict[str, Any]:
    """Waits for the all event to complete"""
    tasks = await _wait_for_many(bot, events, timeout=timeout, return_when=ALL_COMPLETED)
    return {task.get_name(): await task for task in tasks}

async def wait_for_reaction(bot: Bot, check: Callable[[Reaction, Union[User, Member]], bool] = None, timeout: int = None) -> Optional[tuple[Reaction, Union[User, Member]]]:
    """Waits for a reaction add or remove"""
    events = [(event, check) for event in ('reaction_add', 'reaction_remove')]
    name, data = await wait_for_any(bot, *events, timeout=timeout)
    return data