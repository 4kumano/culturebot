from datetime import datetime, timedelta, timezone
from os import name
from typing import Union

import aiohttp
import discord
from discord import Emoji, Member, PartialEmoji, Role, User
from discord.ext import commands
from discord.ext.commands import Bot, Context
from discord.user import ClientUser
from pretty_help import DefaultMenu
from utils import CCog, humandate, utc_as_timezone
import humanize


class Utility(CCog, name="utility"):
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
            r.content_length
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
    async def emojis(self, ctx: Context, emoji: Union[Emoji, PartialEmoji] = None):
        """Shows and manages all emojis in a guild"""
        if emoji:
            return self.emoji_details.invoke(ctx)
        
        guild = ctx.guild
        await ctx.send(f"emojis in {guild}: ({len(guild.emojis)}/{guild.emoji_limit})")
        classic = animated = ''
        for i in guild.emojis:
            if i.animated: animated += str(i)
            else: classic += str(i)
        await ctx.send(classic + '\n' + animated)
    
    @emojis.command('add', aliases=['set', 'edit'])
    @commands.bot_has_permissions(manage_emojis=True)
    async def set_emoji(self, ctx: Context, name: str, emoji: Union[PartialEmoji, str, None] = None, *roles: Role):
        """Adds or sets an emoji to another emoji"""
        if not 2 <= len(name) <= 32:
            raise commands.UserInputError('Name must be between 2 and 32 characters')
        
        if isinstance(emoji, PartialEmoji): # discord emoji
            image = await emoji.url.read()
        else:
            if emoji:
                url = emoji
            elif ctx.message.attachments:
                url = ctx.message.attachments[0].url
            else:
                raise commands.UserInputError('No link/image was provided to set the emoji with')
            
            try:
                async with self.session.get(url) as r:
                    if r.content_length > 0x40000:
                        await ctx.send('File size is bigger than 256kB')
                        return
                    image = await r.read()
            except aiohttp.ClientError:
                await ctx.send(f"The {'image url' if emoji else 'attached image'} is not valid")
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
    
    @commands.group('user', aliases=['member', 'userinfo'])
    async def user(self, ctx: Context, user: Union[Member, User] = None):
        """Shows info about a user"""
        user = user or ctx.author
        if isinstance(user, ClientUser):
            user = ctx.guild.me
        
        if isinstance(user, User):
            embed = discord.Embed(
                colour=discord.Colour.light_grey(),
                description=user.mention
            ).add_field(
                name="Name",
                value=str(user)
            ).add_field(
                name='Account created at',
                value=humandate(user.created_at)
            )
        else:
            embed = discord.Embed(
                colour=user.colour if user.colour.value else discord.Colour.light_grey(),
                description=user.mention
            ).add_field(
                name='Joined at',
                value=humandate(user.joined_at)
            ).add_field(
                name='Account created at',
                value=humandate(user.created_at)
            ).add_field(
                name=f'Roles: {len(user.roles) - 1}',
                value=' '.join(role.mention for role in user.roles if role.position != 0) or user.roles[0].mention,
                inline=False
            ).add_field(
                name='Permissions',
                value=', '.join(name.replace('_', ' ').title() for name, enabled in user.guild_permissions if enabled),
                inline=False
            )
        
        embed.set_author(
            name=user.name,
            icon_url=user.avatar_url
        ).set_thumbnail(
            url=user.avatar_url
        ).set_footer(
            text=f"ID: {user.id}"
        )
        
        await ctx.send(embed=embed)
    
    @commands.command('activity', aliases=['activities'])
    @commands.guild_only()
    async def activity(self, ctx: Context, member: Member = None):
        """Shows the activity of a member."""
        member = member or ctx.author # type: ignore
        if member.activity is None:
            embed = discord.Embed(
                colour=discord.Colour.red(),
                title=f"{member.display_name} does not have any activity"
            ).set_author(
                name=member,
                url=member.avatar_url
            )
            await ctx.send(embed=embed)
            return
        
        embeds = []
        for activity in member.activities:
            if isinstance(activity, discord.Spotify):
                progress = datetime.now().astimezone() - utc_as_timezone(activity.start)
                embed = discord.Embed(
                    colour=activity.colour,
                    title=activity.title,
                    description=f"By: {activity.artist}\n"
                                f"On: {activity.album}"
                ).set_thumbnail(
                    url=activity.album_cover_url
                ).add_field(
                    name="Progress",
                    value=f"{progress.seconds // 60}:{progress.seconds % 60:02d} / "
                          f"{activity.duration.seconds // 60}:{activity.duration.seconds % 60:02d}"
                )
            elif isinstance(activity, discord.Activity):
                if activity.details:
                    embed = discord.Embed(
                        colour=discord.Colour.blurple(),
                        title=activity.details,
                        description=activity.state
                    ).set_author(
                        name=f"{activity.type.name.title()} {activity.name}",
                        icon_url=activity.small_image_url or discord.Embed.Empty,
                        url=activity.url or discord.Embed.Empty
                    )
                else:
                    embed = discord.Embed(
                        colour=discord.Colour.blurple(),
                        title=f"{activity.type.name.title()} {activity.name}",
                    )
                
                embed.set_thumbnail(
                    url=activity.large_image_url or discord.Embed.Empty
                )
                if activity.start:
                    elapsed = datetime.now().astimezone() - utc_as_timezone(activity.start)
                    embed.add_field(
                        name="Elapsed:",
                        value=f"{elapsed.seconds // 3600}:{elapsed.seconds % 3600 // 60}:{elapsed.seconds % 60}"
                    )
            elif isinstance(activity, discord.CustomActivity):
                embed = discord.Embed(
                    colour=discord.Colour.gold(),
                    description=f"**{activity.emoji}** {activity.name}"
                )
            else:
                self.logger.error(f"{activity=}")
                continue
            
            embed.set_footer(
                text=f'Activity of {member}',
                icon_url=member.avatar_url
            )
            embeds.append(embed)
        
        menu = DefaultMenu()
        await menu.send_pages(ctx, ctx, embeds)
        
        

def setup(bot):
    bot.add_cog(Utility(bot))
