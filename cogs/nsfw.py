import io
import random
from typing import Iterable, List, Optional, Sequence, Tuple, Union
import textwrap

import aiohttp
import discord
from discord.abc import Messageable
from discord.channel import TextChannel
from functools import cached_property
from config import config, logger
from discord.ext import commands
from discord.ext.commands import Bot, Context

class SearchError(Exception):
    pass

class NSFW(commands.Cog, name='nsfw'):
    """A cog for sending nsfw images from danbooru."""
    url: str = "https://danbooru.donmai.us/posts.json"
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.session = aiohttp.ClientSession(
            headers={'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"}
        )
        self.danbooru_auth = aiohttp.BasicAuth(
            config['danbooru']['login'], config['danbooru']['api_key']
        )
    
    @commands.Cog.listener()
    async def on_ready(self):
        await self._set_yiff_categories()

    def cog_unload(self):
        if not self.session.closed:
            self.bot.loop.create_task(self.session.close())

    async def search_danbooru(self, tags: Sequence[str], limit: int = 200, rating: Optional[str] = None) -> List[dict]:
        """Searches danbooru for posts."""
        main_tags, filter_tags = tags[:2], tags[2:]
        rating_tag = next((i for i in filter_tags if i.startswith('rating:')), None)
        if rating_tag is not None:
            rating = rating_tag.split(':')[1][0]
        
        url = self.url + '?tags='+'+'.join(main_tags)
        params = {'limit': limit}
        async with self.session.get(url, params=params, auth=self.danbooru_auth) as r:
            posts = await r.json()
            if r.status != 200:
                raise commands.BadArgument(posts['message'])
        
        posts = [
            post for post in posts 
            if post['parent_id'] is None and post.get('file_url') and
            all(tag[1:] not in post['tag_string'] if tag.startswith('-') else tag in post['tag_string'] 
                for tag in filter_tags) and
            (rating is None or post['rating'] == rating)
        ]
        return posts
        
    
    @commands.group('booru', aliases=['danbooru'], invoke_without_command=True)
    @commands.is_nsfw()
    async def booru(self, ctx: Context, *tags: str):
        """Returns a random hot image from the danbooru website
        
        Can take in tags that limits what images can be returned.
        Note that the bot allows more than 2 tags, but those will only be used for filtering.
        That means you the first 2 tags should be the main ones and the other should only be minor filter ones.
        
        https://danbooru.donmai.us/wiki_pages/help:cheatsheet
        """
        posts = await self.search_danbooru(tags)
        if len(posts) == 0:
            await ctx.send(
                f"No posts were returned for `{' '.join(tags)}`\n"
                f"This may be because the tag doesn't exist or "
                f"the combination of tags does not have any posts.")
            return
        
        post = random.choice(posts)
        
        embed = discord.Embed(
            description=f"result for search: `{' '.join(tags)}`", 
            color=discord.Colour.red()
        ).set_author(
            name="danbooru",
            url="https://danbooru.donmai.us/posts?tags="+'+'.join(tags),
            icon_url="https://danbooru.donmai.us/images/danbooru-logo-500x500.png"
        ).add_field(
            name=f"{post['tag_count_general']} tags",
            value=textwrap.shorten(post['tag_string_general'], 1024)
        ).add_field(
            name=f"rating: {post['rating']}",
            value='\u200b'
        ).set_image(
            url=post['file_url']   
        ).set_footer(
            text=f"id: {post['id']} | character: {post['tag_string_character']} | artist: {post['tag_string_artist']}"
        )
        
        await ctx.send(embed=embed)
    
    @booru.command('raw')
    @commands.is_nsfw()
    async def booru_raw(self, ctx: Context, tags: str = '', amount: int = 1):
        """Like booru excepts just sends the image without any embed
        
        If there are multiple tags they must be enclosed in quotes.
        An optional amount may be given, which will send multiple images. Maximum is 10.
        """
        posts = await self.search_danbooru(tags.split())
        if len(posts) == 0:
            await ctx.send(f"No posts were returned for `{tags}`")
            return
        amount = min(amount, 10, len(posts))
        
        images = '\n'.join(post['file_url'] for post in random.sample(posts, amount))
        await ctx.send(images)
        
    
    @booru.command('export', aliases=['txt', 'file'])
    async def booru_export(self, ctx: Context, *tags):
        """Like booru except sends all found images as a list of links in a txt file"""
        posts = await self.search_danbooru(tags)
        images = '\n'.join(post['file_url'] for post in posts)
        file = discord.File(io.BytesIO(images.encode()), f"booru_{'-'.join(tags)}.txt")
        await ctx.send(file=file)
    
    @commands.command('neko')
    async def neko(self, ctx: Context, category: str = 'neko'):
        """Sends a random image from nekos.life"""
        category = category.lower()
        async with self.session.get(f"https://nekos.life/api/v2/img/{category}") as r:
            data = await r.json()
            if data.get('msg') == '404':
                await ctx.send(f'Tag `{category}` does not exist')
                return
            image: str = data['url']
        
        await ctx.send(image)
    
    @commands.command('lewdneko')
    async def lewdneko(self, ctx: Context):
        """Sends a random lewd neko from nekos.life"""
        await self.neko(ctx, 'lewd')
    
    async def _set_yiff_categories(self) -> None:
        """Sets upp yiff categories, should be called only once"""
        async with self.session.get("https://v2.yiff.rest/categories") as r:
            categories = (await r.json())['data']['enabled']
        
        self._yiff_categories: List[List[str]] = [i['db'].split('.') for i in categories if 'animals' not in i['db']]
    
    @commands.command('yiff', aliases=['furry'])
    async def yiff(self, ctx: Context, category = 'Straight'):
        """Sends a random yiff image
        
        If a category is provided the bot sends that specific category
        """
        category = category.lower()
        
        category = discord.utils.find(lambda x: x[-1] == category, self._yiff_categories)
        if category is None:
            await ctx.send(f"Invalid category, must be one of: \n{', '.join(i[-1].title() for i in self._yiff_categories)}")
            return

        category = '/'.join(category)
        async with self.session.get(f"https://v2.yiff.rest/{category}") as r:
            image: dict = (await r.json())['images'][0]
        
        await ctx.send(image['url'])
        
                
    

def setup(bot):
    bot.add_cog(NSFW(bot))
