import asyncio
import random

import discord
from config import config, logger
from discord import Member, User
from discord.ext import commands
from discord.ext.commands import Bot, Context


class Fun(commands.Cog, name="fun"):
    """General "fun" commands to mess around."""

    def __init__(self, bot: Bot):
        self.bot = bot
        self.soundeffect = config['fun']['soundeffect']

    @commands.command('soundeffect', aliases=['sfx'])
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.guild)
    async def play_soundeffect(self, ctx: Context, target: Member = None):
        """Joins user's VC and lets keemstar call him a nice word.

        If I get canceled for this I have no regrets.
        I ain't on twitter anyways.
        Because you bitches were spamming it's now limited to 1 per 5s.
        """
        target = target or ctx.author # type: ignore
        if target.voice is None:
            await ctx.send("Cannot play a soundeffect, the user is not in a vc")
            return
        soundeffect = discord.FFmpegPCMAudio(self.soundeffect)
        try:
            vc = await target.voice.channel.connect()
        except discord.ClientException:
            await ctx.send("Bot is already in a vc.")
            return
        vc.play(soundeffect)
        await asyncio.sleep(1)
        await vc.disconnect()
        logger.debug(f'{ctx.author} played a soundeffect to {target}.')
        
    @commands.command('roll', aliases=['dice', 'diceroll'])
    async def roll(self, ctx: Context, dice: str = '1d6'):
        """Does a random dice roll, must be in the format of 1d6"""
        amount,_,sides = dice.partition('d')
        try:
            amount,sides = int(amount),int(sides)
        except:
            await ctx.send(f"{dice} is not in valid format, must be `<amount>d<side>` (eg 1d6)")
            return
        
        if amount == 1:
            await ctx.send(random.randrange(1, sides))
        else:
            rolls = [random.randrange(1, sides) for _ in range(amount)]
            await ctx.send(', '.join(map(str,rolls)) + f'\ntotal: {sum(rolls)}')
    
    @commands.command('coin', aliases=['toss', 'cointoss'])
    async def coin(self, ctx: Context, heads: str = '', tails: str = ''):
        """Tosses a coin, can take in two random outcomes"""
        if heads and not tails:
            await ctx.send(f"Can't have only one possibility")
            return

        toss = random.random() > 0.5
        await ctx.send(f"Landed on {['Heads', 'Tails'][toss]}" + (f": {[heads,tails][toss]}" if heads else ''))
    
    @commands.command('mention', aliases=['annoy'])
    @commands.has_permissions(mention_everyone=True)
    @commands.guild_only()
    async def mention(self, ctx: Context, type: str = 'here'):
        """Silently mentions all users in a server and deletes the message"""
        perms = ctx.channel.permissions_for(ctx.guild.me) # type: ignore
        if perms.manage_messages:
            await ctx.message.delete()
        msg = await ctx.send('@'+type)
        await msg.delete()


def setup(bot):
    bot.add_cog(Fun(bot))
