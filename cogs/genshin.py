from datetime import datetime

import discord
import genshinstats as gs
from cachetools import TTLCache, cached
from cachetools.keys import hashkey
from discord.ext import commands
from discord.ext.commands import Context
from utils import CCog, asyncify, discord_input, send_pages


class GenshinImpact(CCog):
    """Short description"""
    cache = TTLCache(2048, 300)
    authkeys: dict[int, str] = {}
    
    async def init(self):
        gs.set_cookies(*self.config['cookies'].splitlines())
    
    @cached(cache, key=lambda self, uid, **_: hashkey(uid))
    def _get_user_stats(self, uid: int, cookie = None):
        return gs.get_user_stats(uid, cookie)
    get_user_stats = asyncify(_get_user_stats)

    @asyncify
    @cached(cache, key=lambda self, uid, lang, **_: hashkey(uid, lang))
    def get_characters(self, uid: int, lang: str = 'en-us', cookie = None):
        character_ids = [i['id'] for i in self._get_user_stats(uid)['characters']]
        return gs.get_characters(uid, character_ids, lang, cookie)
    
    @asyncify
    @cached(cache, key=lambda self, uid, previous, **_: hashkey(previous))
    def get_spiral_abyss(self, uid: int, previous: bool = False, cookie = None):
        return gs.get_spiral_abyss(uid, previous, cookie)
    
    @commands.group(invoke_without_command=True, aliases=['gs', 'gi', 'ys'])
    @commands.cooldown(5, 60, commands.BucketType.user)
    async def genshin(self, ctx: Context, uid: int):
        """Shows info about a genshin player"""
        await ctx.trigger_typing()
        try:
            data = await self.get_user_stats(uid)
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
        await send_pages(ctx, ctx, [stats_embed, character_embed, exploration_embed])
    
    @genshin.command('characters')
    @commands.cooldown(5, 60, commands.BucketType.user)
    async def genshin_characters(self, ctx: Context, uid: int, lang: str = 'en-us'):
        """Shows info about a genshin player's characters"""
        await ctx.trigger_typing()
        try:
            data = await self.get_characters(uid, lang)
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
        await send_pages(ctx, ctx, iter(embeds))
        
    @genshin.command('abyss', aliases=['spiral'])
    @commands.cooldown(5, 60, commands.BucketType.user)
    async def genshin_abyss(self, ctx: Context, uid: int, previous: bool = False):
        """Shows info about a genshin player's spiral abyss runs"""
        await ctx.trigger_typing()
        try:
            data = await self.get_spiral_abyss(uid, previous)
        except gs.GenshinStatsException as e:
            await ctx.send(e.msg)
            return
        
        if data['stats']['total_battles'] == 0:
            await ctx.send("This user has not participated in the spiral abyss that season")
            return
        
        embeds = [
            discord.Embed(
                colour=0xffffff,
                title=f"Spiral abyss info of {uid}",
                description="Overall spiral abyss stats"
            ).add_field(
                name="Stats",
                value=f"Total battles: {data['stats']['total_battles']} Total wins: {data['stats']['total_wins']}\n"
                      f"Max floor: {data['stats']['max_floor']} Total stars: {data['stats']['total_stars']}",
                inline=False
            ).add_field(
                name="Character ranks",
                value="\n".join(f"**{k.replace('_',' ')}**: " + ', '.join(f"{i['name']} ({i['value']})" for i in v[:4]) for k,v in data['character_ranks'].items() if v) or "avalible only for floor 9 or above",
                inline=False
            ).set_author(
                name=f"Season {data['season']} ({data['season_start_time']} - {data['season_end_time']})\n"
            ).set_footer(
                text="Powered by genshinstats",
                icon_url="https://yt3.ggpht.com/ytc/AKedOLRtloUOEZcHaRhCYeKyHRg31e54hCcIaVfQ7IN-=s900-c-k-c0x00ffffff-no-rj"
            )
        ]
        for floor in data['floors']:
            embed = discord.Embed(
                colour=0xffffff,
                title=f"Spiral abyss info of {uid}",
                description=f"Floor {floor['floor']} ({floor['stars']} stars)",
                timestamp=datetime.fromisoformat(floor['start'])
            ).set_author(
                name=f"Season {data['season']} (from {data['season_start_time']} to {data['season_end_time']})\n"
            ).set_footer(
                text="Powered by genshinstats",
                icon_url="https://yt3.ggpht.com/ytc/AKedOLRtloUOEZcHaRhCYeKyHRg31e54hCcIaVfQ7IN-=s900-c-k-c0x00ffffff-no-rj"
            )
            for chamber in floor['chambers']:
                for battle in chamber['battles']:
                    embed.add_field(
                        name=f"Chamber {chamber['chamber']}" + (f" Half {battle['half']}" if chamber['has_halves'] else '') + f" ({chamber['stars']} star{'s'*(chamber['stars']!=1)})",
                        value=', '.join(f"{i['name']} (lvl {i['level']})" for i in battle['characters']),
                        inline=False
                    )
            embeds.append(embed)
        await send_pages(ctx, ctx, embeds)
    
    @genshin.command('wishes', aliases=['wish', 'wishHistory'], hidden=True)
    async def genshin_wish_history(self, ctx: Context):
        """Shows your wish history, to view it you must provide your authkey.
        
        For instructions as to how to get the authkey refer to the "auto import" section in https://paimon.moe/wish.
        Sharing this authkey is safe but if you do not feel comfortable sharing it you should run this command in dms.
        """
        authkey = self.authkeys.get(ctx.author.id)
        if authkey is None:
            await ctx.send("Please send your authkey to the bot's dms")
            await ctx.author.send("Please send your authkey: ")
            authkey = await discord_input(ctx.bot, ctx.author, ctx.author)
            if authkey is None:
                await ctx.author.send("Timed out!")
                return
            
            authkey = gs.extract_authkey(authkey.content) or authkey.content
            self.authkeys[ctx.author.id] = authkey
        
        await ctx.send(f"Authkey {authkey!r} is invalid!")
        

def setup(bot):
    bot.add_cog(GenshinImpact(bot))
