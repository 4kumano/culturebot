import difflib
import os
import sys
import textwrap
import time
import traceback
import aiohttp

import discord
from discord import Message
from discord.ext import commands, tasks
from discord.ext.commands import Context
from pretty_help import PrettyHelp

from config import config, logger
from utils import chunkify, confirm, report_bug

class CBot(commands.Bot):
    __slots__ = ()
    
    DEBUG = len(sys.argv) > 1 and sys.argv[1].upper() == 'DEBUG'
    session = aiohttp.ClientSession()
    
    async def close(self) -> None:
        await self.session.close()
        await super().close()
    
    async def on_ready(self):
        logger.info(f'Logged into {len(bot.guilds)} servers.')
        update_hentai_presence.start()
        if bot.DEBUG:
            check_for_update.start()

    async def on_message(self, message: Message):
        if message.author.bot:
            return
        await bot.process_commands(message)

    async def on_message_edit(self, before: Message, after: Message):
        await bot.process_commands(after)

    async def on_command_error(self, ctx: Context, error: Exception):
        if isinstance(error, commands.CommandInvokeError):
            e = error.original
            if await bot.is_owner(ctx.author):
                tb = traceback.format_exception(type(error), error, error.__traceback__)
                for chunk in chunkify(tb, newlines=True, wrapped=True):
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
        
        elif isinstance(error, commands.UserInputError):
            bot.help_command.context = ctx
            signature = bot.help_command.get_command_signature(ctx.command)
            await ctx.send(error.args[0] + f'\nUsage: `{signature}`' )
        
        elif isinstance(error, commands.CommandError):
            await ctx.send(error.args[0])
        
        else:
            raise error

    async def before_invoke(self, ctx: Context):
        cmd_path = ctx.command.full_parent_name.replace(' ', '.')
        command = (cmd_path + '.' if cmd_path else '') + ctx.command.name
        
        content = textwrap.shorten(ctx.message.content, 80, placeholder='...')
        logger.debug(f"g:{ctx.guild.id}/c:{ctx.channel.id}/u:{ctx.author.id}/m:{ctx.message.id} - {command} - \"{content}\"")

    async def after_invoke(self, ctx: Context):
        if ctx.prefix == config['bot']['silent_prefix']:
            try:
                await ctx.message.delete()
            except discord.Forbidden:
                pass


prefixes = (config['bot']['prefix'], config['bot']['silent_prefix'])
bot = CBot(
    commands.when_mentioned_or(*sorted(prefixes, key=len, reverse=True)),
    case_insensitive=True,
    strip_after_prefix=True,
    help_command=PrettyHelp(
        color=0x42F56C,
        ending_note="Prefix: >>",
        show_index=False
    ),
    intents=discord.Intents.all(),
    status=discord.Status.dnd,
    activity=discord.CustomActivity("Reloading bot...", emoji='♻️')
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

@tasks.loop(seconds=60, reconnect=True)
async def update_hentai_presence():
    hentai = await bot.cogs['nsfw'].hanime_random() # type: ignore
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching, 
            name=f"hentai - {hentai[0]['name']}",
        )
    )

@tasks.loop(seconds=1)
async def check_for_update():
    """Debug function that checks for changes in python files"""
    extensions = [
        name
        for name, module in bot.extensions.items()
        if time.time() - os.path.getmtime(module.__file__) < 1
    ]
    for name in extensions:
        try:
            bot.reload_extension(name)
        except commands.ExtensionFailed as e:
            print(f"Could not reload {name}: {e.original}")
        except commands.NoEntryPointError:
            pass
        else:
            print(f"Reloaded {name}")


bot.run(config['bot']['token'])