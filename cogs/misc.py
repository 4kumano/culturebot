import asyncio
import random
from datetime import datetime
from typing import Union
from utils.discord import get_role

import discord
import humanize
from discord import Member, TextChannel, User
from discord.ext import commands
from discord.ext.commands import Context
from utils import CCog, get_webhook, humandate


class Misc(CCog):
    """General miscalenious commands to mess around."""

    @commands.command('soundeffect', aliases=['sfx'])
    @commands.check(lambda ctx: ctx.guild == 790498180504485918)
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.guild)
    async def soundeffect(self, ctx: Context, target: Member = None):
        """Joins user's VC and lets keemstar call him a nice word.

        If I get canceled for this I have no regrets.
        I ain't on twitter anyways.
        Because you bitches were spamming it's now limited to 1 per 5s.
        """
        target = target or ctx.author # type: ignore
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
    async def antitor(self, ctx: Context, ip: str, amount: int = 10):
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
    # random commands
        
    @commands.command('roll', aliases=['dice', 'diceroll'])
    async def roll(self, ctx: Context, dice: str = '1d6'):
        """Does a random dice roll, must be in the format of 1d6"""
        amount,_,sides = dice.partition('d')
        try:
            amount, sides = int(amount), int(sides)
        except:
            await ctx.send(f"{dice} is not in valid format, must be `<amount>d<side>` (eg 1d6)")
            return
        
        if amount == 1:
            await ctx.send(random.randint(1, sides))
        else:
            rolls = [random.randint(1, sides) for _ in range(amount)]
            await ctx.send(', '.join(map(str,rolls)) + f'\ntotal: {sum(rolls)}')
    
    @commands.command('coin', aliases=['toss', 'cointoss'])
    async def coin(self, ctx: Context, heads: str = '', tails: str = ''):
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
    async def mimic(self, ctx: Context, user: Union[Member, User], *, message: str):
        """Sends a webhook message that looks like a user sent it."""
        await ctx.message.delete()
        if user == ctx.bot.user:
            await ctx.send(message)
            return
        webhook = await get_webhook(ctx.channel) # type: ignore
        msg = await webhook.send(message, username=user.display_name, avatar_url=user.avatar_url)

    
    # ============================================================
    # commands admins can use to mess with members
    
    @commands.command('mention', aliases=['annoy'])
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(mention_everyone=True)
    @commands.guild_only()
    async def mention(self, ctx: Context, type: str = 'here'):
        """Silently mentions all users in a server and deletes the message"""
        perms = ctx.channel.permissions_for(ctx.guild.me) # type: ignore
        if perms.manage_messages:
            await ctx.message.delete()
        msg = await ctx.send('@'+type)
        await msg.delete()
        self.logger.debug(f'{ctx.author} mentioned {type}.')
    
    @commands.command('channelswap', aliases=['swapchannels'])
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(manage_channels=True)
    @commands.cooldown(2, 300, commands.BucketType.guild)
    async def channel_swap(self, ctx: Context, a: TextChannel, b: TextChannel):
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
    async def fake_ban(self, ctx: Context, target: Member, seconds: int = 120):
        """Fake bans a member by removing their access to the all channels
        
        Beware: this will cause all permission overwrites to be cleared for them.
        """
        await ctx.message.delete()
        overwrite = discord.PermissionOverwrite(
            view_channel=False
        )
        role = await get_role(target.guild, 'banned', overwrite=overwrite)
        await target.add_roles(role)
        roles = [role for role in target.roles if not role.managed and role.id != role.guild.id]
        await target.remove_roles(*roles)
        
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
        await target.remove_roles(role)
        await target.add_roles(*roles)
        


def setup(bot):
    bot.add_cog(Misc(bot))
