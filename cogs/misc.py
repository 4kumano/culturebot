from __future__ import annotations
import asyncio
import random
from collections import Counter
from datetime import datetime
from typing import Union
from utils.types import GuildContext

import discord
import humanize
from discord.ext import commands
from utils import CCog, get_role, get_webhook, guild_check, humandate


class Misc(CCog):
    """General miscalenious commands to mess around."""
    
    @commands.command('soundeffect', aliases=['sfx'])
    @guild_check(790498180504485918)
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.guild)
    async def soundeffect(self, ctx: GuildContext, target: discord.Member = None):
        """Joins user's VC and lets keemstar call him a nice word.

        If I get canceled for this I have no regrets.
        I ain't on twitter anyways.
        Because you bitches were spamming it's now limited to 1 per 5s.
        """
        target = target or ctx.author
        if target.voice is None or target.voice.channel is None:
            await ctx.send("Cannot play a soundeffect, the user is not in a vc")
            return
        soundeffect = discord.FFmpegPCMAudio(self.config['soundeffect'])
        try:
            vc = await target.voice.channel.connect()
        except discord.ClientException:
            await ctx.send("Bot is already in a vc.")
            return
        vc.play(soundeffect)
        await asyncio.sleep(1)
        await vc.disconnect()
        self.logger.debug(f'{ctx.author} played a soundeffect to {target}.')
    
    @commands.command('antitor', aliases=['iknowwhatyoudownload', 'torrent', 'peer']) 
    @commands.cooldown(rate=1000, per=24*60*60*60, type=lambda msg: 0) # global limit 1000/day
    @commands.cooldown(rate=5, per=60, type=commands.BucketType.user)
    async def antitor(self, ctx: commands.Context, ip: str, amount: int = 10):
        """Shows the torrent history of an ip. Powered by iknowwhatyoudownload.com"""
        async with self.bot.session.get(
            'https://api.antitor.com/history/peer',
            params=dict(ip=ip, contents=min(amount, 20), key=self.config['antitor_key'])
        ) as r:
            data = await r.json()
        
        if 'error' in data:
            raise commands.CommandError(data['message'])
        if not data['contents']:
            await ctx.send("That ip has no torrent history, make sure it's valid.")
            return
        
        geodata = data['geoData']
        embed = discord.Embed(
            colour=0xc9995d,
            title=f"Torrent history for {ip}",
            url=f"https://iknowwhatyoudownload.com/en/peer/?ip={ip}",
            description=f"location: [{geodata['city']}, {geodata['country']}](https://www.openstreetmap.org/?mlat={geodata['latitude']}&mlon={geodata['longitude']}) "
                        f"isp: {data['isp']}"
        )
        for content in data['contents']:
            embed.add_field(
                name=f"{content['name']}",
                value=f"`{content['torrent']['name']}` ({humanize.naturalsize(content['torrent']['size'], True)})\n"
                      f"Category: {content['category']}\n"
                      f"{humandate(datetime.fromisoformat(content['startDate'][:-5]))}",
                inline=False
            )
        await ctx.send(embed=embed)
    
    # ============================================================
    # swears
    
    async def init(self) -> None:
        with open('assets/swears.txt') as file:
            self.swear_words = set(file.read().splitlines())
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        words = Counter(word for word in message.content.split() if word in self.swear_words)
        if not words or sum(words.values()) > 15 or message.guild is None:
            return
        
        await self.bot.db.culturebot.swears.update_one(
            {'member': message.author.id, 'guild': message.guild.id},
            {'$inc': {f'swears.{k}': v for k,v in words.items()} | {'total': sum(words.values())}},
            upsert=True
        )
    
    @commands.command()
    @commands.guild_only()
    async def swears(self, ctx: GuildContext, user: Union[discord.User, discord.Member] = None):
        """Short help"""
        if user is None:
            # there is a proper way to do this but I can't be fucked.
            swears = [
                (doc['member'], doc['swears']) async for doc in 
                self.bot.db.culturebot.swears.find({'guild': ctx.guild.id})
            ]
            swears.sort(key=lambda x: sum(x[1].values()), reverse=True)
            
            if len(swears) == 0:
                await ctx.send("Nobody has ever sworn in this server")
                return
            
            embed = discord.Embed(
                color=discord.Colour.red(),
                title=f"Top 10 users who have sworn the most",
                description=f"List of the top 10 users who have the most of swears in {ctx.guild.name}"
            )
            for rank, (u, s) in enumerate(swears[:10], 1):
                embed.add_field(
                    name=f"{rank} - {self.bot.get_user(u) or await self.bot.fetch_user(u)}",
                    value=f"Sweared **{sum(s.values())}** time{'s'*(len(s)!=1)}.\nMost common swears: " + 
                            '**' + ', '.join(sorted(s.keys(), key=lambda k: -s[k])[:5]) + '**', 
                    inline=False
                )
            await ctx.send(embed=embed)
        else:
            swears = await self.bot.db.culturebot.swears.find_one(
                {'member': user.id, 'guild': ctx.guild.id}
            )
            if swears is None:
                await ctx.send(f"{user} has never sworn in this server")
                return
            embed = discord.Embed(
                color=discord.Colour.red(),
                title=f"Top 10 swears of {user}",
                description=f"List of the top 10 most used swears of {user.mention}"
            ).set_thumbnail(
                url=user.display_avatar.url
            )
            for rank, (swear, amount) in enumerate(Counter(swears['swears']).most_common(10), 1):
                embed.add_field(
                    name=f"{rank} - {swear}", 
                    value=f"Used **{amount}** time{'s'*(amount!=1)}",
                    inline=False
                )
            await ctx.send(embed=embed)

    # ============================================================
    # random commands
        
    @commands.command('roll', aliases=['dice', 'diceroll'])
    async def roll(self, ctx: commands.Context, dice: str = '1d6'):
        """Does a random dice roll, must be in the format of 1d6"""
        amount,_,sides = dice.partition('d')
        try:
            amount, sides = int(amount), int(sides)
        except:
            await ctx.send(f"{dice} is not in valid format, must be `<amount>d<side>` (eg 1d6)")
            return
        
        if amount == 1:
            await ctx.send(str(random.randint(1, sides)))
        else:
            rolls = [random.randint(1, sides) for _ in range(amount)]
            await ctx.send(', '.join(map(str,rolls)) + f'\ntotal: {sum(rolls)}')
    
    @commands.command('coin', aliases=['toss', 'cointoss'])
    async def coin(self, ctx: commands.Context, heads: str = '', tails: str = ''):
        """Tosses a coin, can take in two random outcomes"""
        if heads and not tails:
            await ctx.send(f"Can't have only one possibility")
            return

        toss = random.random() > 0.5
        await ctx.send(f"Landed on {['Heads', 'Tails'][toss]}" + (f": {[heads,tails][toss]}" if heads else ''))
    
    # ============================================================
    # commands that use discord features
    @commands.command()
    @commands.guild_only()
    async def mimic(self, ctx: GuildContext, user: Union[discord.Member, discord.User], *, message: str):
        """Sends a webhook message that looks like a user sent it."""
        await ctx.message.delete()
        if user == ctx.bot.user:
            await ctx.send(message)
            return
        
        webhook = await get_webhook(ctx.channel)
        await webhook.send(
            message,
            username=user.display_name, 
            avatar_url=user.display_avatar.url,
            files=[await i.to_file(spoiler=i.is_spoiler()) for i in ctx.message.attachments if i.size < 0x100000], 
            embeds=ctx.message.embeds
        )

    
    # ============================================================
    # commands admins can use to mess with members
    
    @commands.command('mention', aliases=['annoy'])
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(mention_everyone=True)
    @commands.guild_only()
    async def mention(self, ctx: GuildContext, type: str = 'here'):
        """Silently mentions all users in a server and deletes the message"""
        perms = ctx.channel.permissions_for(ctx.guild.me)
        if perms.manage_messages:
            await ctx.message.delete()
        msg = await ctx.send('@'+type)
        await msg.delete()
        self.logger.debug(f'{ctx.author} mentioned {type}.')
    
    @commands.command('channelswap', aliases=['swapchannels'])
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(manage_channels=True)
    @commands.cooldown(2, 300, commands.BucketType.guild)
    async def channel_swap(self, ctx: commands.Context, a: discord.TextChannel, b: discord.TextChannel):
        """Swaps two channels around, troll some members"""
        old = [{attr:getattr(channel,attr) 
                for attr in ('name', 'position', 'category')} 
               for channel in (a,b)]
        await a.edit(**old[1])
        await b.edit(**old[0])
        await ctx.send('Completed')
        self.logger.debug(f'{ctx.author} swapped {a} and {b}.')
    
    @commands.command('fakeban')
    @commands.bot_has_permissions(manage_channels=True, manage_messages=True)
    @commands.has_guild_permissions(manage_channels=True)
    @commands.cooldown(1, 30, commands.BucketType.guild)
    async def fake_ban(self, ctx: commands.Context, target: discord.Member, seconds: int = 120):
        """Fake bans a member by removing their access to the all channels
        
        Beware: this will cause all permission overwrites to be cleared for them.
        """
        await ctx.message.delete()
        overwrite = discord.PermissionOverwrite(
            view_channel=False
        )
        banned_role = await get_role(target.guild, 'banned', overwrite=overwrite)
        previous_roles = [role for role in target.roles if not role.managed and role.id != role.guild.id]
        await target.remove_roles(*previous_roles)
        await target.add_roles(banned_role)
        
        msg = await ctx.send(f'Banned {target}')
        self.logger.debug(f'{ctx.author} fakebanned {target}.')
        await msg.add_reaction('↩️')
        try:
            await self.bot.wait_for(
                'reaction_add', 
                check=lambda r,u: str(r) == '↩️' and u == ctx.author,
                timeout=max(seconds, 600)
            )
        except asyncio.TimeoutError:
            pass
        
        await msg.clear_reactions()
        await target.add_roles(*previous_roles)
        await target.remove_roles(banned_role)
        


def setup(bot):
    bot.add_cog(Misc(bot))
