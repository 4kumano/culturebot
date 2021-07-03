from __future__ import annotations

from typing import Iterable, Union

from discord import Message
from discord.abc import Messageable

def wrap(*string: str, lang: str = "") -> str:
    """Wraps a string in codeblocks."""
    return f"```{lang}\n" + "".join(string) + "\n```"


def multiline_join(strings: list[str], sep: str = "", prefix: str = "", suffix: str = "") -> str:
    """Like str.join but multiline."""
    parts = zip(*(str(i).splitlines() for i in strings))
    return "\n".join(prefix + sep.join(i) + suffix for i in parts)


def chunkify(string: Union[str, Iterable[str]], max_size: int = 1980, newlines: bool = True, wrapped: bool = False) -> list[str]:
    """Takes in a string or a list of lines and splits it into chunks that fit into a single discord message

    You may change the max_size to make this function work for embeds.
    There is a 20 character leniency given to max_size by default.

    If newlines is true the chunks are formatted with respect to newlines as long as that's possible.
    If wrap is true the chunks will be individually wrapped in codeblocks.
    """
    if newlines:
        string = string.split("\n") if isinstance(string, str) else string

        chunks = [""]
        for i in string:
            i += "\n"
            if len(chunks[-1]) + len(i) < max_size:
                chunks[-1] += i
            elif len(i) > max_size:
                # we don't wrap here because the wrapping will be done no matter what
                chunks.extend(chunkify(i, max_size, newlines=False, wrapped=False))
            else:
                chunks.append(i)
    else:
        string = string if isinstance(string, str) else "\n".join(string)
        chunks = [string[i : i + max_size] for i in range(0, len(string), max_size)]

    if wrapped:
        chunks = [wrap(i) for i in chunks]

    return chunks


async def send_chunks(destination: Messageable, string: Union[str, Iterable[str]], wrapped: bool = False) -> list[Message]:
    """Sends a long string to a channel"""
    return [await destination.send(chunk) for chunk in chunkify(string, wrapped=wrapped)]