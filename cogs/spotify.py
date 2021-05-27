from datetime import datetime
import aiohttp
import discord
from discord.abc import User
from spotipy.cache_handler import CacheFileHandler
from config import config, logger
from discord import Emoji, PartialEmoji, Role
from discord.ext import commands, tasks
from discord.ext.commands import Bot, Context
from utils import CCog

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth

class Spotify(CCog, name="spotify"):
    """Shows what the owner is listening to on spotify"""

    def __init__(self, bot: Bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        auth = SpotifyOAuth(**self.config, cache_handler=CacheFileHandler('credentials/spotipy_cache.json'))
        self.spotify = spotipy.Spotify(oauth_manager=auth)
    
    @commands.Cog.listener()
    async def on_ready(self):
        # refresh token
        self.spotify.auth_manager.get_access_token()
        self.user = self.spotify.me()
    
    @commands.command('spotify')
    async def playing(self, ctx: Context):
        """Shows what the owner is currently listening to"""
        data = self.spotify.currently_playing()
        track = data['item']
        embed = discord.Embed(
            colour=0x1DB954,
            title=track['name'],
            description=f"Artist: {track['artists'][0]['name']}\n"
                        f"Album: {track['album']['name']}",
            url=track['external_urls']['spotify']
        ).set_author(
            name=self.user['display_name'],
            url=self.user['external_urls']['spotify'],
            icon_url=self.user['images'][0]['url']
        ).set_thumbnail(
            url=track['album']['images'][0]['url']
        ).set_footer(
            text=f"progress: {data['progress_ms']//1000}s / {track['duration_ms']//1000}s",
            icon_url='https://developer.spotify.com/assets/branding-guidelines/icon3@2x.png'
        )
        
        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(Spotify(bot))
