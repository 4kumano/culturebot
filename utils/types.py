from typing import Union
import discord
from discord.ext import commands
from typing_extensions import TypeAlias

UserMember: TypeAlias = Union[discord.User, discord.Member]

class GuildContext(commands.Context):
    """A context which doesn't show stupid errors for possible dms"""
    @discord.utils.cached_property
    def guild(self) -> discord.Guild: ...
    @discord.utils.cached_property
    def channel(self) -> discord.TextChannel: ...
    @discord.utils.cached_property
    def author(self) -> discord.Member: ...
    @discord.utils.cached_property
    def me(self) -> discord.Member: ...
