from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Iterable, Sequence

import discord
from discord import Embed, Guild, PermissionOverwrite, Permissions, Role, TextChannel
from discord.abc import Messageable
from discord.ext.commands.context import Context

from .tools import bicycle

if TYPE_CHECKING:
    from discord.webhook import _AsyncWebhook  # discord.py-stubs

async def get_role(guild: Guild, name: str, overwrite: PermissionOverwrite = None, permissions: Permissions = None) -> Role:
    """Returns a role with specific overwrites"""
    role = discord.utils.find(lambda r: r.name.lower() == name, guild.roles)
    
    if role is None:
        role = await guild.create_role(name=name, permissions=permissions or Permissions.none()) # type: ignore
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

async def get_muted_role(guild: Guild) -> Role:
    """Returns the muted role or creates one."""
    overwrite = discord.PermissionOverwrite(
        send_messages=False,
        add_reactions=False
    )
    return await get_role(guild, 'muted', overwrite)

async def get_webhook(channel: TextChannel) -> _AsyncWebhook:
    """Returns the general bot hook or creates one"""
    webhook = discord.utils.find(lambda w: w.name is not None and w.name.lower() == "culture hook", await channel.webhooks())
    
    if webhook is None:
        from bot import bot
        webhook = await channel.create_webhook(name="Culture Hook", avatar=await bot.user.avatar_url.read(), reason="For making better looking messages")

    return webhook

async def _try_delete_reaction(message: discord.Message, payload: discord.RawReactionActionEvent) -> None:
    try:
        await message.remove_reaction(payload.emoji, discord.Object(id=payload.user_id))
    except discord.Forbidden:
        pass

page_left, page_right, remove = "◀", "▶", "❌"
# async def send_pages(ctx: Context, destination: Messageable, embeds: Sequence[Embed], timeout: int = 60):
#     """Send multiple embeds as pages"""
#     message = await destination.send(embed=embeds[0])
#     if len(embeds) == 1:
#         return
    
#     index = 0

#     for reaction in (page_left, page_right, remove):
#         asyncio.create_task(message.add_reaction(reaction))

#     while True:
#         try:
#             payload = await ctx.bot.wait_for(
#                 'raw_reaction_add',
#                 check=lambda payload: payload.user_id != ctx.bot.user.id and message.id == payload.message_id,
#                 timeout=timeout
#             )
#         except asyncio.TimeoutError:
#             await message.clear_reactions()
#             return
        
#         del_task = asyncio.create_task(_try_delete_reaction(message, payload))
        
#         if payload.user_id != ctx.author.id:
#             continue
        
#         r = str(payload.emoji)
#         if r == remove:
#             del_task.cancel()
#             await message.delete()
#             return
#         elif r == page_right:
#             index += 1
#         elif r == page_left:
#             index -= 1
#         else:
#             continue
#         index = index % len(embeds)
#         await message.edit(embed=embeds[index])


async def send_pages(ctx: Context, destination: Messageable, embeds: Iterable[Embed], timeout: int = 60):
    """Send multiple embeds as pages, supports iterators"""
    index = 0
    it = iter(embeds)
    if isinstance(embeds, Sequence):
        depleted = True
    else:
        embeds = [next(it)]
        depleted = False
    message = await destination.send(embed=embeds[0])

    for reaction in (page_left, page_right, remove):
        asyncio.create_task(message.add_reaction(reaction))

    while True:
        try:
            payload = await ctx.bot.wait_for(
                'raw_reaction_add',
                check=lambda payload: payload.user_id != ctx.bot.user.id and message.id == payload.message_id,
                timeout=timeout
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
            index += 1
            if depleted:
                index %= len(embeds)
                embed = embeds[index]
            else:
                embed = next(it, None)
                if embed is None:
                    depleted = True
                    embed = embeds[0]
        elif r == page_left:
            if index == 0 and not depleted:
                continue
            index -= 1
            index %= len(embeds)
            embed = embeds[index]
        else:
            continue
        
        await message.edit(embed=embed)
