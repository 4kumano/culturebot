import difflib
import importlib
import os
import pkgutil
import random
import sys
import textwrap
import time
import traceback
from datetime import datetime
from typing import Optional

import aiohttp
import discord
from discord import Guild, Message
from discord.ext import commands, tasks
from discord.ext.commands import Context
from pretty_help import PrettyHelp

from utils import config, logger, report_bug, send_chunks

__all__ = ['bot']

class CBot(commands.Bot):
    __slots__ = ()

    DEBUG = len(sys.argv) > 1 and sys.argv[1].upper() == "DEBUG"
    config = config
    logger = logger
    start_time = datetime.now()
    prefix_file = 'prefixes.json'
    session: aiohttp.ClientSession
    help_command: commands.HelpCommand
    
    def __init__(self, prefixes: tuple[str, str], **kwargs):
        self.default_command_prefix, self.silent_command_prefix = prefixes
        super().__init__(prefixes, **kwargs)
    
    def run(self, *, reconnect: bool = True) -> None:
        super().run(self.config["bot"]["token"], bot=True, reconnect=reconnect)

    async def start(self, *args, **kwargs) -> None:
        """Starts a bot and all misc tasks"""
        self.session = aiohttp.ClientSession()
        update_hentai_presence.start()
        if bot.DEBUG:
            check_for_update.start()

        await super().start(*args, **kwargs)

    async def close(self) -> None:
        """Closes the bot and its session."""
        await self.session.close()
        await super().close()
    
    async def get_guild_prefix(self, guild: Optional[Guild]) -> list[str]:
        """Returns the prefix for a guild"""
        return [self.default_command_prefix]

    async def get_silent_guild_prefix(self, guild: Optional[Guild]) -> list[str]:
        """Returns the silent prefix for a guild"""
        return [self.silent_command_prefix]
    
    async def get_prefix(self, message: Message) -> list[str]:
        """Returns the prefix"""
        prefixes = await self.get_guild_prefix(message.guild) 
        prefixes.append(self.config['bot']['silent_prefix'])
        prefixes.extend(commands.when_mentioned(self, message))
        return sorted(prefixes, key=len, reverse=True)

    async def on_ready(self):
        logger.info(f"Logged into {len(bot.guilds)} servers.")

    async def on_message_edit(self, before: Message, after: Message):
        if self.user is None:
            return
        await bot.process_commands(after)

    async def on_command_error(self, ctx: Context, error: Exception):
        msg = str(error.args[0]) if error.args else ''
        if isinstance(error, commands.CommandInvokeError):
            e = error.original
            if isinstance(e, NotImplementedError):
                await ctx.send("This command is not avalible")
                return
            if await bot.is_owner(ctx.author):
                tb = traceback.format_exception(type(error), error, error.__traceback__)
                await send_chunks(ctx, tb, wrapped=True)
                return

            await ctx.send("We're sorry, something went wrong. This error has been reported to the owner.")
            await report_bug(ctx, e)

        elif isinstance(error, commands.CommandNotFound):
            if not ctx.invoked_with:
                return

            cmds = [name for name, command in bot.all_commands.items() if not command.hidden]
            match = difflib.get_close_matches(ctx.invoked_with, cmds, 1)
            if match:
                await ctx.send(f"Sorry I don't know what `{ctx.invoked_with}` is, did you perhaps mean `{match[0]}`?")
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


bot = CBot(
    (config["bot"]["prefix"], config["bot"]["silent_prefix"]),
    case_insensitive=True,
    strip_after_prefix=True,
    help_command=PrettyHelp(color=0x42F56C, ending_note=f"Prefix: {config['bot']['prefix']}", show_index=False),
    intents=discord.Intents.all(),
)

@bot.before_invoke
async def before_invoke(ctx: Context):
    """Logs a command to the console along with all neccessary info"""
    if ctx.prefix == config["bot"]["silent_prefix"]:
        try:
            await ctx.message.delete()
        except:
            pass
    
    cmd_path = ctx.command.full_parent_name.replace(" ", ".")
    command = (cmd_path + "." if cmd_path else "") + ctx.command.name

    content = textwrap.shorten(ctx.message.content, 80, placeholder="...")
    logger.debug(f"{ctx.channel.id}/{ctx.message.id} - {command} - \"{content}\"")

@tasks.loop(seconds=60, reconnect=True)
async def update_hentai_presence():
    await bot.wait_until_ready()
    hentai = await bot.cogs["nsfw"].hanime_random()  # type: ignore
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name=f"hentai - {random.choice(hentai[:5])['name']}",
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
        else:
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

for m in pkgutil.iter_modules(['cogs']):
    try:
        bot.load_extension(f"{m.module_finder.path}.{m.name}") # type: ignore
        print(f"Loaded extension '{m.name}'")
    except Exception as e:
        exception = traceback.format_exc()
        logger.error(f"Failed to load extension {m.name}\n{exception}")
