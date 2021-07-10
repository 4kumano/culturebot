from __future__ import annotations

import configparser
import inspect
from logging import Logger
from typing import TYPE_CHECKING, TypeVar

from discord.ext import commands

from .config import config, logger

if TYPE_CHECKING:
    from bot import CBot

T = TypeVar('T')

class CCog(commands.Cog):
    """A cog with a config, logger and an asynchronous init()"""
    __cog_name__: str # discord.py-stubs does not define this???
    bot: CBot
    config: configparser.SectionProxy
    logger: Logger = logger
    
    def __init__(self, bot: CBot) -> None:
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