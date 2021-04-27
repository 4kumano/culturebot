import asyncio
import os
import platform

import discord
from discord import Message
from discord.ext import commands
from pretty_help import PrettyHelp

from config import config, logger

# we fix the shitty bug where when you exit you get a fuck ton of errors
if platform.system() == 'Windows':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

bot = commands.Bot(
    commands.when_mentioned_or(config['bot']['prefix']),
    case_insensitive=True,
    help_command=PrettyHelp(color=0x42F56C)
)

for file in os.listdir('./cogs'):
    if file.endswith(".py"):
        extension = file[:-3]
        try:
            bot.load_extension(f"cogs.{extension}")
            print(f"Loaded extension '{extension}'")
        except Exception as e:
            exception = f"{type(e).__name__}: {e}"
            logger.error(f"Failed to load extension {extension}\n{exception}")

@bot.event
async def on_ready():
	logger.info(f'Logged into {len(bot.guilds)} servers.')

@bot.event
async def on_message(message: Message):
	if message.author.bot:
		return
	await bot.process_commands(message)

bot.run(config['bot']['token'])
