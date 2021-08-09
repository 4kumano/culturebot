from __future__ import annotations

import difflib
import importlib
import os
import random
import sys
import textwrap
import time
import traceback
from datetime import datetime, timedelta
from typing import Iterable, Optional, Union

import aiohttp
import discord
import dislash
import uvicorn
from discord.ext import commands, tasks
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pretty_help import PrettyHelp

from utils import config, humanlist, logger, report_bug, send_chunks

__all__ = ['CBot', 'bot']

class CBot(commands.Bot):
    __slots__ = ()

    DEBUG = len(sys.argv) > 1 and sys.argv[1].upper() == "DEBUG"
    config = config
    logger = logger
    start_time = datetime.now()
    command_prefix: str
    session: aiohttp.ClientSession
    help_command: commands.HelpCommand
    db: AsyncIOMotorDatabase
    slash: dislash.SlashClient
    
    def run(self, *, reconnect: bool = True) -> None:
        super().run(self.config["bot"]["token"], bot=True, reconnect=reconnect)

    async def start(self, *args, **kwargs) -> None:
        """Starts a bot and all misc tasks"""
        self.session = aiohttp.ClientSession()
        self.db = AsyncIOMotorClient(self.config['bot']['mongodb'])
        
        self.loop.create_task(self.start_webapp())
        
        update_hentai_presence.start()
        if self.DEBUG:
            check_for_update.start()

        await super().start(*args, **kwargs)
    
    async def start_webapp(self) -> None:
        """Starts the fastapi app"""
        config = uvicorn.Config('web:app', debug=self.DEBUG, reload=self.DEBUG, use_colors=False)
        self.server = uvicorn.Server(config)
        await self.server.serve()
        await self.close()

    async def close(self) -> None:
        """Closes the bot and its session."""
        await self.session.close()
        await super().close()
    
    async def set_guild_prefix(self, guild: discord.Guild, prefix: Union[str, Iterable[str]]) -> list[str]:
        """Sets the prefix for a guild, returns the previous prefix"""
        if isinstance(prefix, str):
            prefix = [prefix]
        else:
            prefix = list(prefix)
        if prefix == [self.command_prefix]:
            previous = await self.db.culturebot.prefixes.find_one_and_delete({'_id': guild.id})
            return previous['prefix'] if previous else [self.command_prefix]
        
        previous = await self.db.culturebot.prefixes.find_one_and_update(
            {'_id': guild.id}, 
            {'$set': {'prefix': prefix}},
            upsert=True
        )
        return previous['prefix'] if previous else [self.command_prefix]
    
    async def get_guild_prefix(self, guild: Optional[discord.Guild]) -> list[str]:
        """Returns the prefix for a guild"""
        guild_id = guild.id if guild else 0
        prefixes = await self.db.culturebot.prefixes.find_one({'_id': guild_id})
        if prefixes is None:
            return [self.command_prefix]
        return prefixes['prefix']
        
    
    async def get_prefix(self, message: discord.Message) -> list[str]:
        prefixes = await self.get_guild_prefix(message.guild)
        prefixes.extend(commands.when_mentioned(self, message))
        if message.guild is None:
            prefixes.append('')
        return sorted(prefixes, key=len, reverse=True)

    async def on_ready(self):
        logger.info(f"Logged into {len(bot.guilds)} servers.")

    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if datetime.now() - before.created_at > timedelta(minutes=2):
            return
        await bot.process_commands(after)

    async def on_command_error(self, ctx: commands.Context, error: Exception):
        msg = str(error.args[0]) if error.args else ''
        if isinstance(error, commands.CommandInvokeError):
            e = error.original
            if isinstance(e, NotImplementedError):
                await ctx.send("This command is not availible")
                return
            if await bot.is_owner(ctx.author):
                tb = traceback.format_exception(type(error), error, error.__traceback__)
                await send_chunks(ctx, tb, wrapped=True)
                return

            await ctx.send("We're sorry, something went wrong. This error has been reported to the owner.")
            await report_bug(ctx, e)

        elif isinstance(error, commands.CommandNotFound):
            if not ctx.invoked_with or not ctx.invoked_with.strip()[0].isalpha():
                return # wasn't a command at all
            if ctx.prefix == '':
                return # user just sent a random message in dms
            
            cmds = [command.qualified_name for command in bot.commands if not command.hidden]
            matches = difflib.get_close_matches(ctx.invoked_with, cmds)
            if matches:
                await ctx.send(f"Sorry I don't know what `{ctx.invoked_with}` is, did you perhaps mean {humanlist([f'`{i}`' for i in matches], 'or')}?")
            else:
                cmds = [command.qualified_name for command in bot.walk_commands() if not command.hidden]
                matches = difflib.get_close_matches(ctx.invoked_with, cmds)
                if matches:
                    await ctx.send(f"Sorry I don't know what `{ctx.invoked_with}` is, did you perhaps mean {humanlist([f'`{i}`' for i in matches], 'or')}?")
                else:
                    await ctx.send(f"Sorry I don't know what `{ctx.invoked_with}` is.")

        elif isinstance(error, commands.UserInputError):
            bot.help_command.context = ctx
            signature = bot.help_command.get_command_signature(ctx.command)
            await ctx.send(msg + f"\nUsage: `{signature}`")
        
        elif isinstance(error, commands.CheckFailure):
            if msg.startswith('The check functions for '):
                await ctx.send("You are not permitted to run this command")
            else:
                await ctx.send(msg)

        elif isinstance(error, commands.CommandError):
            await ctx.send(msg)

        else:
            raise error
    
    @property
    def uptime(self) -> timedelta:
        return datetime.now() - self.start_time


bot = CBot(
    config["bot"]["prefix"],
    case_insensitive=True,
    strip_after_prefix=True,
    help_command=PrettyHelp(color=0x42F56C, ending_note="Global Prefix: {ctx.bot.command_prefix}"),
    intents=discord.Intents.all(),
)
bot.slash = dislash.SlashClient(bot)

@bot.slash.command(name="help")
async def slash_help(inter: dislash.Interaction):
    await inter.reply("Sorry, slash commands are currently a pain to deal with")

@bot.before_invoke
async def before_invoke(ctx: commands.Context):
    """Logs a command to the console along with all neccessary info"""
    cmd_path = ctx.command.full_parent_name.replace(" ", ".")
    command = (cmd_path + "." if cmd_path else "") + ctx.command.name

    content = textwrap.shorten(ctx.message.content, 80, placeholder="...")
    logger.debug(f"{ctx.channel.id}/{ctx.message.id} - {command} - \"{content}\"")

@tasks.loop(seconds=60, reconnect=True)
async def update_hentai_presence():
    await bot.wait_until_ready()
    hentai = await bot.cogs["NSFW"].hanime_random()  # type: ignore
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name=random.choice(hentai[:5])['name'],
        )
    )


@tasks.loop(seconds=1)
async def check_for_update():
    """Debug function that checks for changes in python files"""
    cwd = os.getcwd()
    extensions = [
        (name, module)
        for name, module in sys.modules.items()
        if getattr(module, "__file__", "") and module.__file__.startswith(cwd) and 
            name != "__main__" and time.time() - os.path.getmtime(module.__file__) < 1
    ]
    for name, module in extensions:
        if name in bot.extensions:
            try:
                bot.reload_extension(name)
            except commands.ExtensionFailed as e:
                print(f"Could not reload {name}: {e.original}")
            except commands.NoEntryPointError:
                pass
            else:
                print(f"Reloaded {name}")
        elif name != 'web':
            try:
                importlib.reload(module)
                # normally you'd reload bot.py itself but that causes a memory leak
                # I can't be fucked to fix this so just reload extensions
                for i in bot.extensions.copy():
                    bot.reload_extension(i)
            except Exception as e:
                print(f"Could not reload {name}: {e}")
            else:
                print(f"Reloaded {name}")

