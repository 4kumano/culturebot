from typing import Union

import aiohttp
import discord
from config import config, logger
from discord import Emoji, PartialEmoji, Role
from discord.ext import commands
from discord.ext.commands import Bot, Context

class Utility(commands.Cog, name="utility"):
    """Manager for Servers, Members, Roles and emojis"""

    def __init__(self, bot: Bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
    
    def cog_unload(self):
        if not self.session.closed:
            self.bot.loop.create_task(self.session.close())
    
    async def _limited_download(self, url: str, max_size: int, chunk_size: int = 0x1000) -> bytes:
        """Downloads a file with a maximum size, if exceeded raises error"""
        async with self.session.get(url) as r:
            content = b''
            while len(content) <= max_size:
                chunk = await r.content.read(chunk_size)
                if chunk == b'':
                    break
                content += chunk
            else:
                raise ValueError(f'File is bigger than {max_size} bytes')
        
        return content

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
    async def set_emoji(self, ctx: Context, name: str, emoji: Union[Emoji, str, None] = None, *roles: Role):
        """Adds or sets an emoji to another emoji"""
        if not 2 <= len(name) <= 32:
            await ctx.send('Name must be between 2 and 32 characters')
            return
        discord.PartialEmoji
        if isinstance(emoji, Emoji):
            image = await emoji.url.read()
        else:
            if emoji:
                url = emoji
            elif ctx.message.attachments:
                url = ctx.message.attachments[0].url
            else:
                await ctx.send('No link/image was provided to set the emoji with')
                return
            
            try:
                image = await self._limited_download(url, 0x40000)
            except aiohttp.ClientError:
                await ctx.send(f"The {'image url' if emoji else 'attached image'} is not valid")
                return
            except ValueError:
                await ctx.send('File size is bigger than 256kB')
                return
        
        existing = discord.utils.get(ctx.guild.emojis, name=name)
        
        try:
            created = await ctx.guild.create_custom_emoji(name=name, image=image, roles=roles)
        except discord.InvalidArgument:
            await ctx.send('Unsupported image type given, can only be jpg, png or gif')
        except discord.HTTPException as e:
            await ctx.send(f'An unexpected error occured: {e}')
        else:
            await ctx.send(f'Successfully created {created}')
            if existing is not None:
                await existing.delete()
        
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
    
    @emojis.command('details', aliases=['show', 'info'])
    async def emoji_details(self, ctx: Context, emoji: Union[Emoji, PartialEmoji]):
        """Shows emoji details"""
        check = '❌', '✅'
        if isinstance(emoji, Emoji):
            description = (
                f"name: {emoji.name}\n"
                f"id: {emoji.id}\n"
                f"guild: {emoji.guild}\n"
                +(f"created by: {emoji.user}\n" if emoji.user else '')+
                f"created at: {emoji.created_at}\n"
                f"{check[emoji.animated]} animated\n"
                f"{check[emoji.managed]} twitch integrated\n"
                f"{check[emoji.available]} avalible\n"
                f"restricted: {', '.join(map(str,emoji.roles)) or 'no'}")
        elif emoji.is_custom_emoji():
            description = (
                f"name: {emoji.name}\n"
                f"id: {emoji.id}\n"
                f"created at: {emoji.created_at}\n"
                f"{check[emoji.animated]} animated\n")
        else:
            await ctx.send('Emoji is not a custom emoji')
            return
        
        embed = discord.Embed(
            title="Emoji details:",
            description=description
        ).set_image(
            url=emoji.url
        ).set_footer(
            text=str(emoji)
        )
        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(Utility(bot))
