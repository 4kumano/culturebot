import io
import json
import random
import re
import textwrap
from typing import List, Optional, Sequence

import aiohttp
import discord
from discord.colour import Colour
from discord.ext import commands
from discord.ext.commands import Bot, Context
from pretty_help import DefaultMenu
from utils import CCog


class SearchError(Exception):
    pass

class NSFW(CCog, name='nsfw'):
    """A cog for sending nsfw images from danbooru."""
    url: str = "https://danbooru.donmai.us/posts.json"
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.session = aiohttp.ClientSession(
            headers={'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"}
        )
        self.danbooru_auth = aiohttp.BasicAuth(
            self.config['login'], self.config['api_key']
        )
    
    @commands.Cog.listener()
    async def on_ready(self):
        await self._set_yiff_categories()

    def cog_unload(self):
        if not self.session.closed:
            self.bot.loop.create_task(self.session.close())

    async def search_danbooru(self, tags: Sequence[str], limit: int = 200, rating: Optional[str] = None) -> List[dict]:
        """Searches danbooru for posts.
        
        Works by using tags for both searching and then filtering.
        This bypasses the need for a premium account.
        """
        # first we separate the main tags from the secondary filter tags
        # the rating tag should be removed from filter tags since it's not really a tag
        main_tags, filter_tags = tags[:2], tags[2:]
        rating_tag = next((i for i in filter_tags if i.startswith('rating:')), None)
        if rating_tag is not None:
            rating = rating_tag.split(':')[1][0]
        
        # then we join the tags into a query param and construct a url
        # we don't use params because that encodes the needed separators
        url = self.url + '?tags='+'+'.join(main_tags)
        params = {'limit': limit}
        # we use authentication so there aren't any ratelimits
        async with self.session.get(url, params=params, auth=self.danbooru_auth) as r:
            posts = await r.json()
            if r.status != 200:
                raise commands.BadArgument(posts['message'])
        
        # finally filter the posts by checking if all filter tags are present
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
        
        embeds = [
            discord.Embed(
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
            for post in posts
        ]
        
        menu = DefaultMenu()
        await menu.send_pages(ctx, ctx, embeds)
    
    @booru.command('raw')
    async def booru_raw(self, ctx: Context, amount: int = 1, *tags: str):
        """Like booru excepts just sends the image without any embed
        
        If there are multiple tags they must be enclosed in quotes.
        An optional amount may be given, which will send multiple images. Maximum is 10.
        """
        posts = await self.search_danbooru(tags)
        if len(posts) == 0:
            await ctx.send(f"No posts were returned for `{' '.join(tags)}`")
            return
        amount = min(amount, 10, len(posts))
        
        images = '\n'.join(post['file_url'] for post in random.sample(posts, amount))
        await ctx.send(images)
        
    
    @booru.command('export', aliases=['txt', 'file'])
    @commands.is_nsfw()
    async def booru_export(self, ctx: Context, *tags):
        """Like booru except sends all found images as a list of links in a txt file"""
        posts = await self.search_danbooru(tags)
        images = '\n'.join(post['file_url'] for post in posts)
        file = discord.File(io.BytesIO(images.encode()), f"booru_{'-'.join(tags)}.txt")
        await ctx.send(file=file)
    
    @commands.command('neko')
    @commands.is_nsfw()
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
    @commands.is_nsfw()
    async def lewdneko(self, ctx: Context):
        """Sends a random lewd neko from nekos.life"""
        await self.neko(ctx, 'lewd')
    
    async def hanime_search(self, query: str) -> list:
        async with self.session.post(
            "https://search.htv-services.com/",
            headers={
                "Content-Type": "application/json;charset=UTF-8"
            },
            json={
                "blacklist": [],
                "brands": [],
                "order_by": "likes",
                "ordering": "desc",
                "page": 0,
                "search_text": query,
                "tags": [],
                "tags_mode": "AND"
            }
        ) as r:
            data = await r.json()
            data = json.loads(data['hits']) # wtf hanime
            return data
    
    async def hanime_random(self) -> list:
        async with self.session.get(
            "https://members.hanime.tv/rapi/v7/hentai_videos",
            params = {
                "source": "randomize",
                "r": round(random.random() * (1 << 8))
            }
        ) as r:
            data = await r.json()
            return sorted(data['hentai_videos'], key=lambda i: i['views'])
    
    @commands.group(invoke_without_command=True)
    @commands.is_nsfw()
    async def hanime(self, ctx: Context, *, query: str = ''):
        """Searches hanime for hentai"""
        if query == '':
            return await self.hanimerandom.invoke(ctx)
        data = await self.hanime_search(query)
        if len(data) == 0:
            await ctx.send(f"No hentai found for query `{query}`")
            return
        embeds = [
            discord.Embed(
                colour=Colour.gold(),
                title=hentai['name'],
                description=re.sub(r'<.+?>', '', hentai['description'])
            ).set_author(
                name=f"Result for search {query}",
                url="https://hanime.tv/videos/hentai/"+hentai['slug']
            ).set_image(
                url=hentai['cover_url']
            ).add_field(
                name="tags",
                value=", ".join(hentai['tags'])
            ).set_footer(
                text=f"{hentai['views']} views | "
                    f"{hentai['likes']} likes & {hentai['dislikes']} dislikes"
            )
            for hentai in data
        ]
        menu = DefaultMenu()
        await menu.send_pages(ctx, ctx, embeds)
    
    @hanime.command('random')
    @commands.is_nsfw()
    async def hanimerandom(self, ctx: Context):
        data = await self.hanime_random()
        embeds = [
            discord.Embed(
                colour=Colour.gold(),
                description=f"{hentai['views']} views\n"
                            f"{hentai['likes']} likes & {hentai['dislikes']} dislikes"
            ).set_author(
                name=hentai['name'],
                url="https://hanime.tv/videos/hentai/"+hentai['slug']
            ).set_image(
                url=hentai['cover_url']
            ).set_footer(
                text=f"page: {i}/{len(data)}"
            )
            for i,hentai in enumerate(data, 1)
        ]
        menu = DefaultMenu()
        await menu.send_pages(ctx, ctx, embeds)
    
    async def _set_yiff_categories(self) -> None:
        """Sets upp yiff categories, should be called only once"""
        async with self.session.get("https://v2.yiff.rest/categories") as r:
            categories = (await r.json())['data']['enabled']
        
        self._yiff_categories: List[List[str]] = [i['db'].split('.') for i in categories if 'animals' not in i['db']]
    
    @commands.command('yiff', aliases=['furry'])
    @commands.is_nsfw()
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
