from __future__ import annotations

from typing import TYPE_CHECKING, Union

import discord
from discord import Guild, Role, TextChannel
from discord.permissions import PermissionOverwrite, Permissions

if TYPE_CHECKING:
    from discord.webhook import _AsyncWebhook # discord.py-stubs

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
