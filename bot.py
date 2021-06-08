import difflib
import os
import traceback

import discord
from discord import Message
from discord.ext import commands
from discord.ext.commands import Context
from pretty_help import PrettyHelp

from config import config, logger
from utils import chunkify, confirm, report_bug

# import platform
# if platform.system() == 'Windows':
#     asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

prefixes = (config['bot']['prefix'], config['bot']['silent_prefix'])

bot = commands.Bot(
    commands.when_mentioned_or(*sorted(prefixes, key=len, reverse=True)),
    case_insensitive=True,
    strip_after_prefix=True,
    help_command=PrettyHelp(
        color=0x42F56C,
        ending_note="Prefix: >>",
        show_index=False
    ),
    intents=discord.Intents.all()
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
    if message.guild and message.guild.id == 842788736008978504 and message.mentions:
        if any(i in message.content for i in ('thanks', 'thank you')):
            await message.add_reaction('👍')
            await message.add_reaction('❌')
    await bot.process_commands(message)

@bot.event
async def on_message_edit(before: Message, after: Message):
    await bot.process_commands(after)

@bot.event
async def on_command_error(ctx: Context, error: Exception):
    if isinstance(error, commands.CommandInvokeError):
        e = error.original
        if await bot.is_owner(ctx.author):
            tb = traceback.format_exception(type(error), error, error.__traceback__)
            for chunk in chunkify(''.join(tb), newlines=True, wrapped=True):
                await ctx.send(chunk)
            return
        
        msg = await ctx.send("We're sorry, something went wrong. Would you like to submit a bug report?")
        if await confirm(bot, msg, ctx.author):
            await ctx.send('Thank you, a bug report has been sent')
            await report_bug(ctx, e)
        else:
            await msg.edit(content="We're sorry, something went wrong")
    
    elif isinstance(error, commands.CommandNotFound):
        if not ctx.invoked_with:
            return
        
        cmds = [name for name,command in bot.all_commands.items() if not command.hidden]
        match = difflib.get_close_matches(ctx.invoked_with, cmds, 1)
        if match:
            await ctx.send(f"Sorry I don't know what `{ctx.invoked_with}` is, did you perhaps mean `{match[0]}`?")
        else:
            await ctx.send(f"Sorry I don't know what `{ctx.invoked_with}` is.")
    
    elif isinstance(error, commands.CommandError):
        await ctx.send(error.args[0])
    
    else:
        raise error

@bot.after_invoke
async def after_invoke(ctx: Context):
    if ctx.prefix == config['bot']['silent_prefix']:
        await ctx.message.delete()

bot.run(config['bot']['token'])
