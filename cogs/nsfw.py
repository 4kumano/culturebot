import random
from typing import List, Union
import textwrap

import aiohttp
import discord
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
            auth=aiohttp.BasicAuth(
                config['danbooru']['login'], config['danbooru']['api_key']
            )
        )

    def cog_unload(self):
        if not self.session.closed:
            self.bot.loop.create_task(self.session.close())

    async def search(self, tags: str, limit: int = 200, nsfw: bool = True) -> Union[List[dict], str]:
        """Searches danbooru for posts."""
        url = self.url + '?tags='+tags
        params = {'limit': limit}
        async with self.session.get(url, params=params) as r:
            posts = await r.json()
            if r.status != 200:
                return posts['message']
        
        posts = [
            post for post in posts 
            if post['parent_id'] is None and post.get('file_url') and
            nsfw or post['rating'] == 's'
        ]
        return posts
    
    @commands.group('booru', aliases=['danbooru'], invoke_without_command=True)
    async def booru(self, ctx: Context, *, tags: str):
        """Returns a random hot image from the danbooru website
        
        Can take in tags that limits what endpoints will be requested.
        
        https://danbooru.donmai.us/wiki_pages/help:cheatsheet
        """
        posts = await self.search(tags.replace(' ', '+'), nsfw=ctx.channel.nsfw or ctx.guild is None)
        if type(posts) is str:
            await ctx.send(posts)
            return
        if len(posts) == 0:
            await ctx.send(
                f"No posts were returned for `{tags}`\n"
                f"This may be because the tag doesn't exist or "
                f"the combination of tags does not have any posts.")
            return
        
        post = random.choice(posts)
        
        embed = discord.Embed(
            description=f"result for search: `{tags}`", 
            color=discord.Colour.red()
        ).set_author(
            name="danbooru",
            url="https://danbooru.donmai.us/posts?tags="+tags.replace(' ', '+'),
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
    async def rawbooru(self, ctx: Context, tags: str = '', amount: int = 1):
        """Like booru excepts just sends the image without any embed
        
        If there are multiple tags they must be enclosed in quotes.
        An optional amount may be given, which will send multiple images. Maximum is 10.
        """
        posts = await self.search(tags.replace(' ', '+'), nsfw=ctx.channel.nsfw or ctx.guild is None)
        if len(posts) == 0:
            await ctx.send(f"No posts were returned for `{tags}`")
            return
        if type(posts) is str:
            await ctx.send(posts)
            return
        amount = min(amount, 10, len(posts))
        
        images = '\n'.join(post['file_url'] for post in random.sample(posts, amount))
        await ctx.send(images)
        
    
    @commands.command('rawbooru', aliases=['rawdanbooru', 'rbooru'], help=rawbooru.help)
    async def rawbooru_shortcut(self, ctx: Context, tags: str = '', amount: int = 1):
        """Shortcut for "booru raw" """
        await self.rawbooru(ctx, tags, amount)
    

def setup(bot):
    bot.add_cog(NSFW(bot))
