from datetime import datetime

import aiohttp
import discord
from config import config, logger
from discord import TextChannel
from discord.ext import commands, tasks
from discord.ext.commands import Bot, Context


class Anilist(commands.Cog, name="github"):
    """A bot that posts whatever anime the owner watches."""
    url = "https://api.github.com/repos/{user}/{repo}/commits"
    channel: TextChannel

    def __init__(self, bot: Bot):
        self.bot = bot
        self.user = config['github']['user']
        self.repos = config['github']['repos'].split(',')
        self.token = config['github']['token']
        self.session = aiohttp.ClientSession()

    @commands.Cog.listener()
    async def on_ready(self):
        self.channel = await self.bot.fetch_channel(config['github'].getint('channel'))
        self.fetch_commits.start()

    def cog_unload(self):
        self.fetch_commits.cancel()
        if not self.session.closed:
            self.bot.loop.create_task(self.session.close())

    @tasks.loop(minutes=10)
    async def fetch_commits(self):
        """Fetches new github commits"""
        for repo in self.repos:
            since = datetime.min
            async for msg in self.channel.history():
                if not msg.embeds:
                    continue
                e = msg.embeds[0]
                if e.title == 'github commit' and repo in e.description:
                    since = e.timestamp
                    break
            await self.update_commit_activity(repo, since)

    async def update_commit_activity(self, repo: str, since: datetime):
        async with self.session.get(
            self.url.format(user=self.user, repo=repo),
            params=dict(since=since.isoformat(), per_page=100),
            headers={"Authorization": f"token {self.token}"}
        ) as r:
            data = await r.json()
        
        for commit in reversed(data):
            commmit_name, _, message = commit['commit']['message'].partition(
                '\n\n')
            embed = discord.Embed(
                title="github commit",
                description=f"New commit in [{repo}]({commit['html_url']})",
                color=0x211F1F,
                timestamp=datetime.fromisoformat(
                    commit['commit']['author']['date'][:-1])
            ).set_author(
                name=commit['author']['login'],
                url=commit['author']['html_url'],
                icon_url=commit['author']['avatar_url']
            ).add_field(
                name=commmit_name.strip(),
                value=message.strip() or "\u200b",
                inline=False
            ).set_footer(
                text=commit['sha'],
                icon_url="https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png"
            )

            await self.channel.send(embed=embed)
            
            logger.info(f"Updated github commit {commit['sha']}")


def setup(bot):
    bot.add_cog(Anilist(bot))
