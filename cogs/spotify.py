import discord
import requests
import spotipy
from discord.ext import commands, tasks
from spotipy import CacheFileHandler, SpotifyOAuth
from utils import CCog, coroutine


class Spotify(CCog):
    """Shows what the owner is listening to on spotify"""
    _session = requests.Session()
    
    def __init__(self, bot):
        self.spotify = spotipy.Spotify(
            requests_session=self._session, 
            oauth_manager=SpotifyOAuth(
                **self.config, 
                cache_handler=CacheFileHandler('credentials/spotipy_cache.json')
            )
        )
    
    async def init(self):
        self.keep_token_alive.start()
        try:
            user = await self.bot.loop.run_in_executor(None, self.spotify.me)
        except Exception as e:
            self.logger.error(e)
            self.bot.remove_cog(self.__cog_name__)
            return
        
        if user is None:
            self.logger.error("The user wasn't found")
            self.bot.remove_cog(self.__cog_name__)
            return
        
        self.user = user
    
    def cog_unload(self) -> None:
        self._session.close()
    
    @commands.command('spotify')
    @commands.is_owner()
    async def playing(self, ctx: commands.Context):
        """Shows what the owner is currently listening to"""
        data = await coroutine(self.spotify.currently_playing)()
        if data is None:
            await ctx.send("The user doesn't seem to be currently playing anything")
            return
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
    @coroutine
    def keep_token_alive(self):
        """Keep refreshing the access token every <1h
        
        This is due to a bug I don't understand
        """
        self.spotify.auth_manager.get_access_token() # type: ignore

def setup(bot):
    bot.add_cog(Spotify(bot))
