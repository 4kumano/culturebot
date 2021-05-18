from typing import Union

import aiohttp
import discord
from config import config, logger
from discord.emoji import Emoji
from discord.ext import commands
from discord.ext.commands import Bot, Context


class Utility(commands.Cog, name="utility"):
    """Moderation commands and shit"""

    def __init__(self, bot: Bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
    
    def cog_unload(self):
        if not self.session.closed:
            self.bot.loop.create_task(self.session.close())

    @commands.group('emojis', aliases=['emoji', 'emote', 'emotes'], invoke_without_command=True)
    @commands.guild_only()
    async def emojis(self, ctx: Context):
        """Shows and manages all emojis in a guild"""
        guild = ctx.guild
        await ctx.send(f"emojis in {guild}: ({len(guild.emojis)}/{guild.emoji_limit})")
        classic = animated = ''
        for i in guild.emojis:
            if i.animated: animated += str(i)
            else: classic += str(i)
        await ctx.send(classic + '\n' + animated)
    
    @emojis.command('add', aliases=['set', 'edit'])
    @commands.bot_has_permissions(manage_emojis=True)
    async def set_emoji(self, ctx: Context, name: str, emoji: Union[Emoji, str, None] = None):
        """Adds or sets an emoji to another emoji"""
        if not 2 <= len(name) <= 32:
            await ctx.send('Name must be between 2 and 32 characters')
            return
        
        if isinstance(emoji, Emoji):
            image = await emoji.url.read()
        else:
            if emoji:
                url = emoji
            else:
                if ctx.message.attachments:
                    url = ctx.message.attachments[0].url
                else:
                    await ctx.send('No link/image was provided to set the emoji with')
                    return
            try:
                async with self.session.get(url) as r:
                    image = await r.read()
            except:
                await ctx.send('Image is not valid')
                return
        
        existing = discord.utils.get(ctx.guild.emojis, name=name)
        if existing is not None:
            await existing.delete()
        
        try:
            created = await ctx.guild.create_custom_emoji(name=name, image=image)
        except discord.InvalidArgument:
            await ctx.send('Unsupported image type given, can only be jpg, png or gif')
        else:
            await ctx.send(f'Successfully created {created}')
        
    @emojis.command('rename')
    @commands.bot_has_permissions(manage_emojis=True)
    async def rename_emoji(self, ctx: Context, emoji: Emoji, name: str):
        """Renames an emoji"""
        await emoji.edit(name=name)
        await ctx.send(f'Renamed {emoji}')
    
    @emojis.command('delete', aliases=['remove', 'del'])
    @commands.bot_has_permissions(manage_emojis=True)
    async def delete_emoji(self, ctx: Context, emoji: Emoji):
        """Deletes an emoji"""
        await emoji.delete()
        await ctx.send(f'Deleted \\:{emoji.name}\\:')


def setup(bot):
    bot.add_cog(Utility(bot))
