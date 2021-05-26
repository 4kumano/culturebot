from datetime import datetime
import difflib
import importlib.util
import os
import traceback

from discord.enums import ActivityType
from utils import chunkify, confirm, wrap

import discord
from discord import Color, Message
from discord.channel import TextChannel
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

prefixes = (config['bot']['prefix'], config['bot']['silent_prefix'])
class PrettyHelpFix(PrettyHelp):
    """A fix for a cog bug in PrettyHelp"""
    async def send_pages(self):
        try:
            await super().send_pages()
        except IndexError:
            x: discord.TextChannel = self.get_destination()
            x.typing()

bot = commands.Bot(
    commands.when_mentioned_or(*sorted(prefixes, key=len, reverse=True)),
    case_insensitive=True,
    strip_after_prefix=True,
    help_command=PrettyHelpFix(
        color=0x42F56C,
        ending_note="Prefix: >>",
        show_index=False
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
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="hentai"))

@bot.event
async def on_message(message: Message):
    if message.author.bot:
        return
    await bot.process_commands(message)

async def report_bug(ctx: Context, error: Exception):
    """Reports a bug to a channel"""
    channel_id = config['bot'].getint('bugreport')
    channel = bot.get_channel(channel_id) or await bot.fetch_channel(channel_id)
    if not isinstance(channel ,TextChannel):
        raise ValueError(f'Bug report channel is not a text channel, but a {type(channel)}')

    tb = traceback.format_exception(type(error), error, error.__traceback__)
    chunks = chunkify(''.join(tb), 1000, newlines=True, wrapped=True)
    
    embed = discord.Embed(
        color=discord.Colour.red(),
        title=type(error).__name__,
        url=ctx.message.jump_url,
        timestamp=datetime.now()
    ).set_author(
        name=str(ctx.author),
        icon_url=ctx.author.avatar_url
    )
    for chunk in chunks:
        embed.add_field(
            name='\u200b​',
            value=chunk,
            inline=False
        )
    
    await channel.send(embed=embed)

@bot.event
async def on_command_error(ctx: Context, error: Exception):
    msg = error.args[0]
    if isinstance(error, commands.CommandInvokeError):
        e = error.original
        msg = await ctx.send("We're sorry, something went wrong. Would you like to submit a bug report?")
        if await confirm(bot, msg, ctx.author):
            await ctx.send('Thank you, a bug report has been sent')
            await report_bug(ctx, e)
        else:
            await msg.edit(content="We're sorry, something went wrong")
    
    elif isinstance(error, commands.CommandNotFound):
        if not ctx.invoked_with:
            return
        match = difflib.get_close_matches(ctx.invoked_with, list(bot.all_commands), 1)
        if match:
            await ctx.send(f"Sorry I don't know what `{ctx.invoked_with}` is, did you perhaps mean `{match[0]}`?")
        else:
            await ctx.send(f"Sorry I don't know what `{ctx.invoked_with}` is.")
    
    elif isinstance(error, commands.CommandError):
        await ctx.send(msg)
    
    else:
        raise error

@bot.after_invoke
async def after_invoke(ctx: Context):
    if ctx.prefix == config['bot']['silent_prefix']:
        await ctx.message.delete()

bot.run(config['bot']['token'])
