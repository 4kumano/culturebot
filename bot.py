import difflib
import importlib.util
import os
import traceback

import discord
from discord import Color, Message
from discord.ext import commands
from discord.ext.commands import Context
from discord.ext.commands.errors import CommandError
from pretty_help import PrettyHelp

from config import config, logger

# # we fix the shitty bug where when you exit you get a fuck ton of errors
# import platform
# if platform.system() == 'Windows':
#     asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(
    commands.when_mentioned_or(config['bot']['prefix']),
    case_insensitive=True,
    help_command=PrettyHelp(
        color=0x42F56C,
        ending_note="Prefix: c!",
        show_index=True
    ),
    intents=intents
)

for file in os.listdir('./cogs'):
    if file[0] == '_':
        continue
    extension = os.path.splitext(file)[0]
    try:
        bot.load_extension(f"cogs.{extension}")
        print(f"Loaded extension '{extension}'")
    except Exception as e:
        exception = traceback.format_exc()
        logger.error(f"Failed to load extension {extension}\n{exception}")

@bot.event
async def on_ready():
    logger.info(f'Logged into {len(bot.guilds)} servers.')

@bot.event
async def on_message(message: Message):
    if message.author.bot:
        return
    await bot.process_commands(message)


@bot.event
async def on_command_error(ctx: Context, error: Exception):
    msg = error.args[0]
    if isinstance(error, commands.CommandInvokeError):
        e = error.original
        tb = traceback.format_exception(type(e),e,e.__traceback__)
        await ctx.send('Something went horribly wrong, this is the traceback:')
        await ctx.send('```\n'+''.join(tb)[:1990]+'```')
    elif isinstance(error, commands.CommandNotFound):
        if not ctx.invoked_with:
            return
        match = difflib.get_close_matches(ctx.invoked_with, list(bot.all_commands), 1)
        if match:
            await ctx.send(f"Sorry I don't know what that is, did you perhaps mean `{match[0]}`?")
        else:
            await ctx.send(f"Sorry I don't know what that is.")
    elif isinstance(error, commands.CommandError):
        await ctx.send(f":exclamation: {msg}",delete_after=10)
    else:
        raise error

bot.run(config['bot']['token'])
