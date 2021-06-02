from datetime import datetime, timedelta

import aiohttp
import discord
from discord import TextChannel
from discord.ext import commands, tasks
from discord.ext.commands import Bot, Context
from utils import CCog


class Osu(CCog, name="osu"):
    """A bot that posts whatever anime the owner watches."""
    expires_in: datetime = datetime.min
    access_token: str
    channel: TextChannel

    def __init__(self, bot: Bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.client_id = self.config['clientid']
        self.client_secret = self.config['secret']

    @commands.Cog.listener()
    async def on_ready(self):
        self.channel = await self.bot.fetch_channel(self.config.getint('channel')) # type: ignore
        self.fetch_scores.start()

    def cog_unload(self):
        self.fetch_scores.stop()
        if not self.session.closed:
            self.bot.loop.create_task(self.session.close())

    async def renew_access_token(self):
        async with self.session.post(
            "https://osu.ppy.sh/oauth/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": "public"
            }
        ) as r:
            data = await r.json()
        self.access_token = data['access_token']
        self.expires_in = datetime.now() + timedelta(seconds=data['expires_in'])

    async def request(self, url, **kwargs):
        """Requests an osu url"""
        if self.expires_in < datetime.now():
            await self.renew_access_token()
        
        headers = {'Authorization': f"Bearer {self.access_token}"}
        async with self.session.get(url, headers=headers, **kwargs) as r:
            return await r.json()
    
    @tasks.loop(minutes=10)
    async def fetch_scores(self):
        """Fetches new best scores."""
        last = datetime.min
        async for msg in self.channel.history():
            if not msg.embeds:
                continue
            e = msg.embeds[0]
            if msg.embeds and e.title == 'osu highscore' and e.timestamp:
                last = e.timestamp
                break
        
        data: list = await self.request('https://osu.ppy.sh/api/v2/users/16573307/scores/best?limit=20')
        data.sort(key=lambda x: x['created_at'])
        
        for score in data[-10:]:
            t = datetime.fromisoformat(score['created_at']).replace(tzinfo=None)
            if t <= last:
                continue
            
            embed = discord.Embed(
                title="osu highscore", 
                description=f"A new top 20 score:\n[{score['beatmapset']['title']}]({score['beatmap']['url']})", 
                color=0xff66aa,
                timestamp=t
            ).set_author(
                name=score['user']['username'], 
                url=f"https://osu.ppy.sh/users/{score['user']['id']}", 
                icon_url=score['user']['avatar_url']
            ).set_thumbnail(
                url=score['beatmapset']['covers']['list@2x']
            ).add_field(
                name="stats", 
                value=f"version: {score['beatmap']['version']} ({score['beatmap']['difficulty_rating']} stars)\n"
                      f"{round(score['pp'])}pp | rank {score['rank']} | {round(score['accuracy']*100,2)}% accuracy | {score['score']} score ", 
                inline=False
            ).set_footer(
                text=f"Weighted pp: {round(score['weight']['pp'],2)}",
                icon_url="https://i.ppy.sh/013ed2c11b34720790e74035d9f49078d5e9aa64/68747470733a2f2f6f73752e7070792e73682f77696b692f696d616765732f4272616e645f6964656e746974795f67756964656c696e65732f696d672f75736167652d66756c6c2d636f6c6f75722e706e67"
            )
            
            await self.channel.send(embed=embed)
            
            self.logger.info(f"Updated osu score {score['best_id']}")
        
            
                


def setup(bot):
    bot.add_cog(Osu(bot))
