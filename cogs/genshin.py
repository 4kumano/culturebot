import asyncio
import discord
import genshinstats as gs
from discord.ext import commands
from discord.ext.commands import Context
from pretty_help.menu import DefaultMenu
from utils import CCog


class Genshin(CCog):
    """Short description"""
    async def init(self):
        gs.set_cookies(*self.config['cookies'].splitlines())
    
    @commands.group(invoke_without_command=True)
    @commands.cooldown(5, 60, commands.BucketType.user)
    async def genshin(self, ctx: Context, uid: int):
        """Shows info about a genshin player"""
        await ctx.trigger_typing()
        try:
            data = await asyncio.to_thread(gs.get_user_stats, uid)
        except gs.GenshinStatsException as e:
            await ctx.send(e.msg)
            return

        stats_embed = discord.Embed(
            colour=0xffffff,
            title=f"Info about {uid}",
            description="Basic user stats"
        ).set_footer(
            text="Powered by genshinstats",
            icon_url="https://yt3.ggpht.com/ytc/AKedOLRtloUOEZcHaRhCYeKyHRg31e54hCcIaVfQ7IN-=s900-c-k-c0x00ffffff-no-rj"
        )
        for field, value in data['stats'].items():
            stats_embed.add_field(
                name=field.replace('_', ' '),
                value=value
            )
        
        character_embed = discord.Embed(
            colour=0xffffff,
            title=f"Info about {uid}",
            description="Basic character info (only first 15)"
        ).set_footer(
            text="Powered by genshinstats",
            icon_url="https://yt3.ggpht.com/ytc/AKedOLRtloUOEZcHaRhCYeKyHRg31e54hCcIaVfQ7IN-=s900-c-k-c0x00ffffff-no-rj"
        )
        characters = sorted(data['characters'], key=lambda x: -x['level'])
        for char in characters[:15]:
            character_embed.add_field(
                name=f"{char['name']}",
                value=f"{char['rarity']}* {char['element']}\nlvl {char['level']}, friendship {char['friendship']}"
            )
        
        exploration_embed = discord.Embed(
            colour=0xffffff,
            title=f"Info about {uid}",
            description="Basic exploration info"
        ).set_footer(
            text="Powered by genshinstats",
            icon_url="https://yt3.ggpht.com/ytc/AKedOLRtloUOEZcHaRhCYeKyHRg31e54hCcIaVfQ7IN-=s900-c-k-c0x00ffffff-no-rj"
        )
        for city in data['explorations']:
            exploration_embed.add_field(
                name=city['name'],
                value=f"explored {city['explored']}% ({city['type']} lvl {city['level']})",
                inline=False
            )
        menu = DefaultMenu()
        await menu.send_pages(ctx, ctx, [stats_embed, character_embed, exploration_embed])
    
    @genshin.command('characters')
    async def genshin_characters(self, ctx: Context, uid: int, lang: str = 'en-us'):
        """Shows info about a genshin player's characters"""
        await ctx.trigger_typing()
        try:
            data = await asyncio.to_thread(gs.get_characters, uid, lang=lang)
        except gs.GenshinStatsException as e:
            await ctx.send(e.msg)
            return

        embeds = [
            discord.Embed(
                colour=0xffffff,
                title=char['name'],
                description=f"{char['rarity']}* {char['element']}\n"
                            f"level {char['level']} C{char['constellation']}"
            ).set_thumbnail(
                url=char['weapon']['icon']
            ).set_image(
                url=char['icon']
            ).add_field(
                name=f"Weapon: {char['weapon']['name']}",
                value=f"{char['weapon']['rarity']}* {char['weapon']['type']}\n"
                      f"level {char['weapon']['level']} refinement {char['weapon']['refinement']}",
                inline=False
            ).add_field(
                name=f"Artifacts",
                value="\n".join(f"{i['pos_name'].title()}: {i['set']['name']} - {i['rarity']}* level {i['level']}" for i in char['artifacts']) or 'none eqipped',
                inline=False
            ).set_footer(
                text="Powered by genshinstats",
                icon_url="https://yt3.ggpht.com/ytc/AKedOLRtloUOEZcHaRhCYeKyHRg31e54hCcIaVfQ7IN-=s900-c-k-c0x00ffffff-no-rj"
            )
            for char in data
        ]
        menu = DefaultMenu()
        await menu.send_pages(ctx, ctx, embeds)
        

def setup(bot):
    bot.add_cog(Genshin(bot))
