import asyncio
from typing import Dict, List, Optional

import discord
from discord.channel import TextChannel
from config import config, logger
from discord import Member, User
from discord.ext import commands
from discord.ext.commands import Bot, Context


class Fun(commands.Cog, name="fun"):
    """General "fun" commands to mess around."""
    def __init__(self, bot: Bot):
        self.bot = bot
        self.soundeffect = config['fun']['soundeffect']
    
    @commands.command('soundeffect',aliases=[config['fun'].get('soundeffectname')])
    @commands.cooldown(rate=1,per=5,type=commands.BucketType.guild)
    async def play_soundeffect(self, ctx: Context, target: Member = None):
        """Joins user's VC and lets keemstar call him a nice word.
        
        If I get canceled for this I have no regrets.
        I ain't on twitter anyways.
        Because you bitches were spamming it's now limited to 1 per 5s.
        """
        target = target or ctx.author
        soundeffect = discord.FFmpegPCMAudio(self.soundeffect)
        try:
            vc = await target.voice.channel.connect()
        except discord.ClientException:
            await ctx.send("Bot is already in a vc.")
            return
        vc.play(soundeffect)
        await asyncio.sleep(1)
        await vc.disconnect()
        logger.debug(f'Played a soundeffect to {target}.')
        


def setup(bot):
    bot.add_cog(Fun(bot))
