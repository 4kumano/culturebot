from datetime import datetime

import aiohttp
import discord
from discord import TextChannel
from discord.ext import commands, tasks
from discord.ext.commands import Bot, Context
from utils import CCog


class Github(CCog, name="github"):
    """A bot that posts whatever anime the owner watches."""
    url = "https://api.github.com/repos/{user}/{repo}/commits"
    channel: TextChannel

    async def init(self):
        await self.bot.wait_until_ready()
        self.channel = await self.bot.fetch_channel(self.config.getint('channel')) # type: ignore
        self.fetch_commits.start()

    def cog_unload(self):
        self.fetch_commits.cancel()

    @tasks.loop(minutes=10)
    async def fetch_commits(self):
        """Fetches new github commits"""
        for repo in self.config['repos'].split(','):
            since = datetime.min
            async for msg in self.channel.history():
                if not msg.embeds:
                    continue
                e = msg.embeds[0]
                if e.title == 'github commit' and e.timestamp and repo in e.description: # type: ignore
                    since = e.timestamp
                    break
            await self.update_commit_activity(repo, since)

    async def update_commit_activity(self, repo: str, since: datetime):
        async with self.bot.session.get(
            self.url.format(user=self.config['user'], repo=repo),
            params=dict(since=since.isoformat(), per_page=100),
            headers={"Authorization": f"token {self.config['token']}"}
        ) as r:
            data = await r.json()
        
        for commit in reversed(data):
            commmit_name, _, message = commit['commit']['message'].partition('\n\n')
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
                value=message.strip()[:1024] or "\u200b",
                inline=False
            ).set_footer(
                text=commit['sha'],
                icon_url="https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png"
            )

            await self.channel.send(embed=embed)
            
            self.logger.info(f"Updated github commit {commit['sha']}")


def setup(bot):
    bot.add_cog(Github(bot))
