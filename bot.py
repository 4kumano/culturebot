import os

import traceback
import discord
from discord import Message, Color
from discord.ext import commands
from discord.ext.commands import Context
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
    if file.endswith(".py"):
        extension = file[:-3]
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
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.CommandError):
        await ctx.send(f":exclamation: {msg}",delete_after=10)
    else:
        raise error

bot.run(config['bot']['token'])
