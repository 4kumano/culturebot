from datetime import datetime, timedelta, timezone

import aiohttp
import discord
from config import config, logger
from discord import TextChannel
from discord.ext import commands, tasks
from discord.ext.commands import Bot, Context


class Anilist(commands.Cog, name="anilist"):
    """A bot that posts whatever anime the owner watches."""
    url = "https://graphql.anilist.co"
    query = """
query ($id: Int, $last: Int) {
  User(id: $id) {
    name
    avatar {
      large
    }
    siteUrl
  }
  Page(page: 1) {
    activities(userId: $id, type: MEDIA_LIST, sort: ID_DESC, createdAt_greater: $last) {
      ... on ListActivity {
        id
        type
        status
        progress
        createdAt
        media {
          id
          type
          bannerImage
          siteUrl
          title {
            userPreferred
          }
          coverImage {
            large
          }
        }
      }
    }
  }
}
    """
    channel: TextChannel

    def __init__(self, bot: Bot):
        self.bot = bot
        self.userid = config['anilist']['userid']
        self.session = aiohttp.ClientSession()

    @commands.Cog.listener()
    async def on_ready(self):
        self.channel = await self.bot.fetch_channel(config['anilist'].getint('channel')) # type: ignore
        self.fetch_activity.start()

    def cog_unload(self):
        self.fetch_activity.cancel()
        if not self.session.closed:
            self.bot.loop.create_task(self.session.close())

    @tasks.loop(minutes=10)
    async def fetch_activity(self):
        """Fetches new anilist activity.
        
        Doesn't give a fuck about timezones because I don't either.
        """
        last = 0
        async for msg in self.channel.history():
            if not msg.embeds:
                continue
            e = msg.embeds[0]
            if msg.embeds and e.title == 'anilist status':
                last = int(e.timestamp.timestamp())
                break

        data = await self.fetch_anilist(self.query, {'id': self.userid, 'last': last})

        user = data['User']
        for activity in reversed(data['Page']['activities']):
            anime = f"[{activity['media']['title']['userPreferred']}]({activity['media']['siteUrl']})"
            if activity['progress']:
                description = f"{activity['status']} {activity['progress']} of {anime}"
            else:
                description = f"{activity['status']} {anime}"
            
            embed = discord.Embed(
                title="anilist status",
                description=description,
                color=discord.Color.green(),
                timestamp=datetime.fromtimestamp(activity['createdAt'])
            ).set_author(
                name=user['name'],
                url=user['siteUrl'],
                icon_url=user['avatar']['large']
            ).set_thumbnail(
                url=activity['media']['coverImage']['large']
            ).set_footer(
                text=f"{'anime' if activity['type']=='ANIME_LIST' else 'manga'} activity",
                icon_url="https://anilist.co/img/icons/android-chrome-512x512.png"
            )
            await self.channel.send(embed=embed)

            logger.info(f"Updated anilist activity {activity['id']}")

    async def fetch_anilist(self, query: str, variables: dict, **kwargs):
        """Fetches data from anilist api."""
        payload = {'query': query, 'variables': variables}
        async with self.session.post(self.url, json=payload, **kwargs) as r:
            data = await r.json()
        return data['data']


def setup(bot):
    bot.add_cog(Anilist(bot))
