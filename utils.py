from __future__ import annotations

import asyncio
from typing import Optional, TypeVar, Union

from discord import Message, User
from discord.ext.commands import Bot
from discord.member import Member

T = TypeVar('T')


def multiline_join(strings: list[str], sep: str = '', prefix: str = '', suffix: str = '') -> str:
    """Like str.join but multiline."""
    parts = zip(*(str(i).splitlines() for i in strings))
    return '\n'.join(prefix+sep.join(i)+suffix for i in parts)


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
