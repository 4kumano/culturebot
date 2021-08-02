from __future__ import annotations
import re
from datetime import datetime, timedelta
from typing import Any, Union

import discord
import humanize
from discord.ext import commands, tasks
from utils import CCog, humandate

OSU_LOGO = "https://i.ppy.sh/013ed2c11b34720790e74035d9f49078d5e9aa64/68747470733a2f2f6f73752e7070792e73682f77696b692f696d616765732f4272616e645f6964656e746974795f67756964656c696e65732f696d672f75736167652d66756c6c2d636f6c6f75722e706e67"

class Osu(CCog):
    """Osu! users and beatmaps"""
    url = "https://osu.ppy.sh/api/v2"
    
    expires_in: datetime = datetime.min
    access_token: str
    channel: discord.TextChannel
    
    limit: int = 20


    async def init(self):
        await self.bot.wait_until_ready()
        self.channel = await self.bot.fetch_channel(self.config.getint('channel')) # type: ignore
        self.fetch_scores.start()

    def cog_unload(self):
        self.fetch_scores.stop()

    async def renew_access_token(self):
        async with self.bot.session.post(
            "https://osu.ppy.sh/oauth/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self.config['clientid'],
                "client_secret": self.config['secret'],
                "scope": "public"
            }
        ) as r:
            data = await r.json()
        self.access_token = data['access_token']
        self.expires_in = datetime.now() + timedelta(seconds=data['expires_in'])

    async def request(self, url: str, **kwargs) -> Any:
        """Requests an osu url"""
        if self.expires_in < datetime.now():
            await self.renew_access_token()
        
        headers = {'Authorization': f"Bearer {self.access_token}"}
        url = self.url + url
        async with self.bot.session.get(url, headers=headers, **kwargs) as r:
            return await r.json(content_type=None)
    
    @tasks.loop(minutes=10)
    async def fetch_scores(self):
        """Fetches new best scores."""
        await self.bot.wait_until_ready()
        
        last = datetime.min
        async for msg in self.channel.history(limit=None):
            if not msg.embeds:
                continue
            e = msg.embeds[0]
            if msg.embeds and e.title == 'osu highscore' and e.timestamp:
                last = e.timestamp
                break
        
        data: list = await self.request(
            f"/users/{self.config['userid']}/scores/best", 
            params=dict(limit=self.limit)
        )
        data.sort(key=lambda x: x['created_at'])
        
        for score in data[-10:]:
            t = datetime.fromisoformat(score['created_at']).replace(tzinfo=None)
            if t <= last:
                continue
            
            embed = discord.Embed(
                title="osu highscore", 
                description=f"A new top {self.limit} score:\n"
                            f"[{score['beatmapset']['title']}]({score['beatmap']['url']})", 
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
                      f"{round(score['pp'])}pp | rank {score['rank']} | "
                      f"{round(score['accuracy']*100, 2)}% accuracy | {score['score']} score ", 
                inline=False
            ).set_footer(
                text=f"Weighted pp: {round(score['weight']['pp'],2)}",
                icon_url=OSU_LOGO
            )
            
            await self.channel.send(embed=embed)
            
            self.logger.info(f"Updated osu score {score['best_id']}")
        
    @commands.group('osu', invoke_without_command=True)
    async def osu(self, ctx: commands.Context):
        """Shows info about osu users and beatmaps."""
        await self.osu_user.invoke(ctx)
    
    @osu.group('user', invoke_without_command=True)
    async def osu_user(self, ctx: commands.Context, user: str, mode: str = ''):
        """Shows basic user info"""
        data = await self.request(f"/users/{user}/{mode}")
        stats = data['statistics']
        
        last_visit = datetime.fromisoformat(data['last_visit']) - datetime.now().astimezone()
        disc = data['discord'].split('#')
        disc = discord.utils.get(self.bot.users, name=disc[0], discriminator=disc[1])
        
        embed = discord.Embed(
            colour=0xff66aa,
            title="osu! profile",
            description=f"Global rank: #**{stats['global_rank']}** | Country rank (**{data['country_code']}**): #**{stats['country_rank']}**\n"
                        f"Play time: **{stats['play_time']}**s | **{stats['pp']}** pp | Hit accuracy: **{stats['hit_accuracy']}**%\n"
        ).set_author(
            name=data['username'], 
            url=f"https://osu.ppy.sh/users/{data['id']}", 
            icon_url=data['avatar_url']
        ).add_field(
            name="About me: ",
            value=f"Joined {humandate(datetime.fromisoformat(data['join_date']))} | "
                  f"Last online {humanize.naturaldelta(last_visit) if last_visit.total_seconds() > 300 else 'now'}\n"
                  f"Plays with **{', '.join(data['playstyle'])}** | Favorite playmode: **{data['playmode']}**\n"
                  f"Location: **{data['location']}** | Interests: **{data['interests']}** | Occupation: **{data['occupation']}**\n"
                  f"Twitter: **[{data['twitter']}](https://twitter.com/{data['twitter'].strip('@')})** | Discord: **{disc.mention if disc else data['discord']}** | Website: **{data['website']}**"
                         
        )
        await ctx.send(embed=embed)
    
    @osu.group('beatmap', aliases=['map'])
    async def osu_beatmap(self, ctx: commands.Context, beatmap: Union[int, str]):
        """Shows beatmap info
        
        Takes in either the beatmap id or the url.
        Note that beatmap and beatmapsets are different things
        """
        if isinstance(beatmap, str):
            match = re.search(r"(?:beatmapsets/\d+#osu|beatmaps)/(\d+)", beatmap)
            if match is None:
                raise commands.BadArgument("Expected a beatmap id or a beatmap url")
            beatmap = match.group(1)
        
        data = await self.request(f"/beatmaps/{beatmap}")
        beatmapset = data['beatmapset']
        del data['failtimes']
        embed = discord.Embed(
            colour=0xff66aa,
            title="osu! beatmap"
        ).set_author(
            name=beatmapset['title'],
            url=data['url'],
            icon_url=beatmapset['covers']['list']
        ).set_image(
            url=beatmapset['covers']['cover@2x']
        ).add_field(
            name="Version",
            value=f"Version: **{data['version']}** | Difficulty: **{data['difficulty_rating']}** stars\n"
                  f"ar: **{data['ar']}** | cs: **{data['cs']}** | acc: **{data['accuracy']}** | drain: **{data['drain']}**\n"
                  f"Total plays: **{data['playcount']:,}** | Total passes: **{data['passcount']:,}** (**{data['passcount']/data['playcount']*100:.2f}%**)"
        ).set_footer(
            text=f"id: {data['id']}"    
        )
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Osu(bot))
