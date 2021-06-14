import aiohttp
import discord
import spotipy
from discord.ext import commands, tasks
from discord.ext.commands import Bot, Context
from spotipy import CacheFileHandler, SpotifyOAuth
from utils import CCog, asyncify


class Spotify(CCog, name="spotify"):
    """Shows what the owner is listening to on spotify"""

    def __init__(self, bot: Bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        auth = SpotifyOAuth(**self.config, cache_handler=CacheFileHandler('credentials/spotipy_cache.json'))
        self.spotify = spotipy.Spotify(oauth_manager=auth)
        self.keep_token_alive.start()
    
    @commands.Cog.listener()
    async def on_ready(self):
        try:
            self.user = await asyncify(self.spotify.me)()
        except Exception as e:
            self.logger.error(e)
            self.bot.remove_cog(self.__cog_name__)
    
    @commands.command('spotify')
    async def playing(self, ctx: Context):
        """Shows what the owner is currently listening to"""
        data = await asyncify(self.spotify.currently_playing)()
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
    
    @tasks.loop(minutes=59, seconds=15)
    @asyncify
    def keep_token_alive(self):
        """Keep refreshing the access token every <1h
        
        This is due to a bug I don't understand
        """
        self.spotify.auth_manager.get_access_token()

def setup(bot):
    bot.add_cog(Spotify(bot))
