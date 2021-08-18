from __future__ import annotations

from datetime import datetime, timedelta
import random
from utils.types import GuildContext

import discord
from discord.ext import commands, tasks
from utils import CCog


class XP(CCog):
    """Short description"""
    last_messages: dict[discord.Member, datetime] = {}
    ratelimit = timedelta(minutes=2)
    
    async def init(self):
        await self.bot.wait_until_ready()
        self.db = self.bot.db.xp
        self.last_messages_cleanup.start()
        
    @tasks.loop(minutes=10)
    async def last_messages_cleanup(self):
        now = datetime.now()
        members = list(self.last_messages.keys()) # create copy
        for m in members:
            if now - self.last_messages[m] > self.ratelimit:
                del self.last_messages[m]
    
    async def give_xp(self, member: discord.Member):
        await self.bot.wait_until_ready()
        settings = await self.db.settings.find_one(
            {'id': member.guild.id, 'amount': {'$exists': True}}
        )
        amount = settings['msgxp'] if settings else random.randint(10, 20)
        
        await self.db.xp.update_one(
            {'guild': member.guild.id, 'member': member.id},
            {'$inc': {'xp': amount}},
            upsert=True
        )
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not isinstance(message.author, discord.Member) or message.author.bot:
            return
        
        # skip bot commands and the like
        if len(message.content) <= 10 or not all(i==' ' or i.isalpha() for i in message.content[:5]):
            return
        
        last = self.last_messages.get(message.author)
        if last is None or datetime.now() - last > self.ratelimit:
            self.last_messages[message.author] = datetime.now()
            await self.give_xp(message.author)
    
    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    async def xp(self, ctx: GuildContext, member: discord.Member = None):
        """Show a member's current xp"""
        member = member or ctx.author
        data = await self.db.xp.find_one(
            {'guild': ctx.guild.id, 'member': member.id}
        )
        if data is None:
            await ctx.send(f"{member} has never spoken in this server")
            return

        xp = data['xp']
        await ctx.send(f"You have {xp} xp")
    
    @xp.command(aliases=['lb'])
    @commands.guild_only()
    async def leaderboard(self, ctx: GuildContext):
        """Show a leaderboard of the top most active members"""
        cursor = self.db.xp.find({'guild': ctx.guild.id}).sort('xp', -1).limit(10)
        embed = discord.Embed(
            colour=discord.Colour.blurple(),
            title="XP Leaderboard",
            description=f"Leaderboard of the most active users in {ctx.guild}"
        )
        i = 1
        async for data in cursor:
            user = self.bot.get_user(data['member']) or self.bot.fetch_user(data['member'])
            embed.add_field(
                name=f"{i}. {user}",
                value=f"{data['xp']}xp",
                inline=False
            )
            i += 1
        
        await ctx.send(embed=embed)
        
        
    

def setup(bot):
    bot.add_cog(XP(bot))
