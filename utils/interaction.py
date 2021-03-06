from __future__ import annotations

import asyncio
import traceback
from datetime import datetime
from typing import Mapping, Optional, TypeVar, Union

import discord
from discord.ext import commands

from .config import config
from .formatting import chunkify
from .tools import zip_once

T = TypeVar("T")


async def report_bug(ctx: commands.Context, error: Exception, description: str = ""):
    """Reports a bug to a channel"""
    channel_id = config["bot"].getint("bugreport")
    channel = ctx.bot.get_channel(channel_id) or await ctx.bot.fetch_channel(channel_id)
    assert isinstance(channel, discord.TextChannel)

    tb = traceback.format_exception(type(error), error, error.__traceback__)

    embed = discord.Embed(
        color=discord.Colour.red(), title="A bug was encountered!", url=ctx.message.jump_url, timestamp=datetime.now()
    )
    embed.set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)

    for chunk, name in zip_once(chunkify(description, 1000, wrapped=True), "description"):
        embed.add_field(name=name, value=chunk, inline=False)

    for chunk, name in zip_once(chunkify(tb, 1000, wrapped=True), "traceback"):
        embed.add_field(name=name, value=chunk, inline=False)

    await channel.send(embed=embed)


async def confirm(bot: commands.Bot, message: discord.Message, user: discord.abc.User, timeout: int = 15) -> bool:
    """Confirms a message"""
    yes, no = "✅", "❌"
    await message.add_reaction(yes)
    await message.add_reaction(no)
    try:
        reaction, _ = await bot.wait_for(
            "reaction_add", check=lambda r, u: str(r) in (yes, no) and u == user, timeout=timeout
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
    bot: commands.Bot,
    message: discord.Message,
    user: Union[discord.User, discord.Member],
    choices: Union[Mapping[str, T], list[T]],
    timeout: float = 60,
    delete_after_timeout: bool = True,
    cancel: Optional[str] = "❌",
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
        reactions = {getattr(i, "value", str(i)).strip(): i for i in choices}

    for i in reactions:
        await message.add_reaction(i)
    if cancel:
        await message.add_reaction(cancel)

    try:
        reaction, _ = await bot.wait_for(
            "reaction_add", 
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
        except discord.NotFound:
            return None

    if str(reaction) == cancel:
        await message.delete()
        return None

    return reactions[str(reaction)]


async def discord_input(
    bot: commands.Bot, user: Union[discord.User, discord.Member], channel: discord.abc.Messageable, timeout: int = 60
) -> Optional[discord.Message]:
    if isinstance(channel, (discord.User, discord.Member)):
        channel = channel.dm_channel or await channel.create_dm()
    try:
        return await bot.wait_for("message", check=lambda m: m.author == user and m.channel == channel, timeout=timeout)
    except asyncio.TimeoutError:
        return None
