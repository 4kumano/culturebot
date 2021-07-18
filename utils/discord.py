from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, AsyncIterable, Iterable, Union

import discord
from discord.ext import commands

from .tools import AsyncPaginator, Paginator

if TYPE_CHECKING:
    from discord.webhook import _AsyncWebhook  # discord.py-stubs


async def get_role(
    guild: discord.Guild,
    name: str,
    overwrite: discord.PermissionOverwrite = None,
    permissions: discord.Permissions = None,
) -> discord.Role:
    """Returns a role with specific overwrites"""
    role = discord.utils.find(lambda r: r.name.lower() == name.lower(), guild.roles)

    if role is None:
        role = await guild.create_role(name=name, permissions=permissions or Permissions.none())  # type: ignore
    elif permissions is not None and role.permissions != permissions:
        await role.edit(permissions=permissions)

    if overwrite is None:
        return role

    for channel in guild.channels:
        if channel.category and channel.permissions_synced:
            channel = channel.category
        if channel.overwrites_for(role) != overwrite:
            await channel.set_permissions(role, overwrite=overwrite)

    return role


async def get_muted_role(guild: discord.Guild) -> discord.Role:
    """Returns the muted role or creates one."""
    overwrite = discord.PermissionOverwrite(send_messages=False, add_reactions=False)
    return await get_role(guild, "muted", overwrite)


async def get_webhook(channel: discord.TextChannel) -> _AsyncWebhook:
    """Returns the general bot hook or creates one"""
    webhook = discord.utils.find(
        lambda w: w.name is not None and w.name.lower() == "culture hook", await channel.webhooks()
    )

    if webhook is None:
        from bot import bot

        webhook = await channel.create_webhook(
            name="Culture Hook", avatar=await bot.user.avatar_url.read(), reason="For making better looking messages"
        )

    return webhook


async def _try_delete_reaction(message: discord.Message, payload: discord.RawReactionActionEvent) -> None:
    try:
        await message.remove_reaction(payload.emoji, discord.Object(id=payload.user_id))
    except discord.Forbidden:
        pass

page_left, page_right, remove = "◀", "▶", "❌"
async def send_pages(
    ctx: commands.Context,
    destination: discord.abc.Messageable,
    pages: Union[Iterable[discord.Embed], AsyncIterable[discord.Embed]],
    asyncify: bool = False,
    timeout: int = 60,
):
    """Send multiple embeds as pages, supports iterators

    If asyncify is true the items will be gotten asynchronously even with sync iterables.
    """
    paginator = AsyncPaginator(pages)
    message = await destination.send(embed=await paginator.acurr())

    for reaction in (page_left, page_right, remove):
        asyncio.create_task(message.add_reaction(reaction))

    while True:
        try:
            payload = await ctx.bot.wait_for(
                "raw_reaction_add",
                check=lambda payload: payload.user_id != ctx.bot.user.id and message.id == payload.message_id,
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            await message.clear_reactions()
            return

        del_task = asyncio.create_task(_try_delete_reaction(message, payload))

        if payload.user_id != ctx.author.id:
            continue

        r = str(payload.emoji)
        if r == remove:
            del_task.cancel()
            await message.delete()
            return
        elif r == page_right:
            embed = await paginator.next(asyncify=asyncify)
        elif r == page_left:
            try:
                embed = paginator.prev()
            except IndexError:
                continue
        else:
            continue

        await message.edit(embed=embed)
