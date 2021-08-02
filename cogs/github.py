from __future__ import annotations
from datetime import datetime

import discord
from discord.ext import commands, tasks
from utils import CCog


class Github(CCog):
    """Show info about a github user or repository"""
    channel: discord.TextChannel

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
        r =  await self.bot.session.get(
            f"https://api.github.com/repos/{self.config['user']}/{repo}/commits",
            params=dict(since=since.isoformat(), per_page=100),
            headers={"Authorization": f"token {self.config['token']}"}
        )
        data = await r.json()
        
        for commit in reversed(data):
            commmit_name, _, message = commit['commit']['message'].partition('\n\n')
            embed = discord.Embed(
                title="github commit",
                description=f"New commit in [{repo}]({commit['html_url']})",
                color=0x211F1F,
                timestamp=datetime.fromisoformat(commit['commit']['author']['date'][:-1])
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
    
    @commands.command(usage="<user>[/repo]")
    async def github(self, ctx: commands.Context, *, path: str):
        """Shows info about a github user/repository
        
        Provide as "thesadru" or "thesadru/culturebot"
        """
        user, _, repo = path.replace(' ', '/', 1).partition('/')
        if repo:
            async with self.bot.session.get(
                f"https://api.github.com/repos/{user}/{repo}",
                headers={"Authorization": f"token {self.config['token']}"}
            ) as r:
                data = await r.json()
            embed = discord.Embed(
                title=data['full_name'],
                description=f"stars: {data['stargazers_count']} forks: {data['forks_count']}\n"
                            f"language: {data['language']} license: {data['license']['name'] if data['license'] else 'no'}\n"
                            +(f"homepage: {data['homepage']}" if data['homepage'] else ''),
                url=data['html_url']
            ).set_author(
                name=data['owner']['login'],
                url=data['owner']['html_url'],
                icon_url=data['owner']['avatar_url']
            ).set_thumbnail(
                url=data['owner']['avatar_url']
            ).add_field(
                name="Description",
                value=data['description']
            )
            await ctx.send(embed=embed)
        else:
            async with self.bot.session.get(
                f"https://api.github.com/users/{user}",
                headers={"Authorization": f"token {self.config['token']}"}
            ) as r:
                data = await r.json()
            embed = discord.Embed(
                title=f"{data['name']} ({data['login']})",
                description=f"repos: {data['public_repos']} gists: {data['public_gists']}\n"
                            f"followers: {data['followers']} following: {data['following']}\n"
                            f"location: {data['location']}",
                url=data['html_url']
            ).set_thumbnail(
                url=data['avatar_url']
            ).add_field(
                name="Bio",
                value=data['bio']
            ).add_field(
                name="Contact",
                value=''.join([
                    (f"email: [{data['email']}](mailto:{data['email']})\n" if data['email'] else ''),
                    (f"twitter: [{data['twitter_username']}](https://twitter.com/{data['twitter_username']})\n" if data['twitter_username'] else ''),
                    (f"company: {data['company']}\n" if data['company'] else ''),
                    
                ]) or 'no contact avalible'
            ).set_footer(
                text=f"id: {data['id']}"
            )
            await ctx.send(embed=embed)
        


def setup(bot):
    bot.add_cog(Github(bot))
