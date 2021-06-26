from __future__ import annotations

import asyncio
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from functools import partial
from typing import Any, Callable, Coroutine, Optional, TypeVar

import discord
from discord.ext import commands
from discord.ext.commands import Context

T = TypeVar("T")


def humandate(dt: Optional[datetime]) -> str:
    if dt is None:
        return "unknown"
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


async_executor = ThreadPoolExecutor()


def asyncify(func: Callable[..., T]) -> Callable[..., Coroutine[Any, Any, T]]:
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
