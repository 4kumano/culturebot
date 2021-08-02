from __future__ import annotations
import asyncio
import json
from datetime import datetime, timedelta
from itertools import groupby
from typing import Optional, Union

import discord
import genshinstats as gs
from cachetools import TTLCache, cached
from cachetools.keys import hashkey
from discord.ext import commands
from utils import (CCog, coroutine, discord_input, grouper, send_pages,
                   to_thread)

GENSHIN_LOGO = "https://yt3.ggpht.com/ytc/AKedOLRtloUOEZcHaRhCYeKyHRg31e54hCcIaVfQ7IN-=s900-c-k-c0x00ffffff-no-rj"

def _item_color(rarity: int = 0) -> int:
    if rarity == 5:
        return 0xf1c40f # gold
    elif rarity == 4:
        return 0x9b59b6 # purple
    elif rarity == 3:
        return 0x3498db # blue
    else:
        return 0xffffff # white

def _character_icon(name: str, image: bool = False) -> str:
    name = name.title().replace('_', ' ')
    name = {
        "Amber": "Ambor",
        "Jean": "Qin",
        "Noelle": "Noel",
        "Traveler": "PlayerBoy"
    }.get(name, name)
    if image:
        return f"https://upload-os-bbs.mihoyo.com/game_record/genshin/character_image/UI_AvatarIcon_{name}@2x.png"
    else:
        return f"https://upload-os-bbs.mihoyo.com/game_record/genshin/character_icon/UI_AvatarIcon_{name}.png"

base = "https://webstatic-sea.hoyolab.com/app/community-game-records-sea/images/"
abyss_banners = {
    0:  base + "pc-abyss-bg.dc0c3ac6.png",
    9:  base + "pc9.1f1920d2.png",
    10: base + "pc10.b0019d93.png",
    11: base + "pc11.38507e1e.png",
    12: base + "pc12.43f28b10.png",
}

class GenshinImpact(CCog):
    """Show info about Genshin Impact users using mihoyo's api"""
    icon_cache: dict[int, str] = {}
    
    async def init(self):
        with open(self.config['cookie_file']) as file:
            cookies = json.load(file)
        gs.set_cookies(*cookies)
        
        await self.bot.wait_until_ready()
        self.db = self.bot.db.genshin
    
    def _element_emoji(self, element: str) -> discord.Emoji:
        g = self.bot.get_guild(570841314200125460) or self.bot.guilds[0]
        e = discord.utils.get(g.emojis, name=element.lower()) or discord.Emoji()
        return e
    
    async def _user_uid(self, user: discord.abc.User) -> Optional[int]:
        """Returns the user's uid as in the database"""
        data = await self.db.users.find_one(
            {'discord_id': user.id, 'uid': {'$exists': True}}
        )
        return data['uid'] if data else None
    
    @cached(TTLCache(2048, 3600), key=lambda self, uid, **_: hashkey(uid))
    def _get_user_stats(self, uid: int, cookie = None):
        return gs.get_user_stats(uid, cookie)
    get_user_stats = coroutine(_get_user_stats)

    @coroutine
    @cached(TTLCache(2048, 3600), key=lambda self, uid, lang, **_: hashkey(uid, lang))
    def get_characters(self, uid: int, lang: str = 'en-us', cookie = None):
        character_ids = [i['id'] for i in self._get_user_stats(uid)['characters']]
        characters = gs.get_characters(uid, character_ids, lang, cookie)
        for c in characters:
            self.icon_cache[c['name']] = c['icon']
            self.icon_cache[c['weapon']['name']] = c['weapon']['icon']
        return characters
    
    @coroutine
    @cached(TTLCache(2048, 3600), key=lambda self, uid, previous, **_: hashkey(uid, previous))
    def get_spiral_abyss(self, uid: int, previous: bool = False, cookie = None):
        return gs.get_spiral_abyss(uid, previous, cookie)

    async def update_users_cache(self):
        """Updates the user cache in the database"""
        await self.bot.wait_until_ready()
        
        already_fetched: set[int] = set()
        already_fetched_hoyolab: set[int] = set()
        async for i in self.db.users.find({'hoyolab_uid': {'$exists': True}}):
            already_fetched.add(i['uid'])
            already_fetched_hoyolab.add(i['hoyolab_uid'])
        
        users = await to_thread(gs.get_recommended_users)
        for i, user in enumerate(users):
            if i % 25 == 0:
                # swap cookies for efficency
                gs.genshinstats.cookies.append(gs.genshinstats.cookies.pop(0))
            hoyolab_uid = int(user['user']['uid'])
            print(hoyolab_uid)
            if hoyolab_uid in already_fetched_hoyolab:
                continue
            await asyncio.sleep(1) # avoid ratelimit
            card = await to_thread(gs.get_record_card, hoyolab_uid)
            if card is None:
                continue
            uid = int(card['game_role_id'])
            if uid in already_fetched:
                continue
            
            await self.db.users.insert_one(
                {'uid': uid, 'hoyolab_uid': hoyolab_uid}
            )
    
    @commands.group(invoke_without_command=True, aliases=['gs', 'gi', 'ys'])
    @commands.cooldown(5, 60, commands.BucketType.user)
    async def genshin(self, ctx: commands.Context, user: Union[discord.User, int] = None):
        """Shows info about a genshin player"""
        if isinstance(user, int):
            uid = user
        else:
            uid = await self._user_uid(user or ctx.author)
            if uid is None:
                if user is None:
                    await ctx.send(f"Either provide a uid or set your own uid with `{ctx.prefix}genshin setuid`")
                else:
                    await ctx.send(f"User does not have a uid set")
                return
        
        await ctx.trigger_typing()
        try:
            data = await self.get_user_stats(uid)
        except gs.GenshinStatsException as e:
            await ctx.send(e.msg)
            return

        pages = []
        
        stats_embed = discord.Embed(
            colour=0xffffff,
            title=f"Info about {uid}",
            description="Basic user stats"
        ).set_footer(
            text="Powered by genshinstats",
            icon_url=GENSHIN_LOGO
        )
        for field, value in data['stats'].items():
            stats_embed.add_field(
                name=field.replace('_', ' '),
                value=value
            )
        pages.append(stats_embed)
        
        exploration_embed = discord.Embed(
            colour=0xffffff,
            title=f"Info about {uid}",
            description="Basic exploration info"
        ).set_footer(
            text="Powered by genshinstats",
            icon_url=GENSHIN_LOGO
        )
        for city in reversed(data['explorations']):
            exploration_embed.add_field(
                name=city['name'],
                value=f"explored {city['explored']}% ({city['type']} lvl {city['level']})\n" + 
                      ', '.join(f"{i['name']} lvl {i['level']}" for i in city['offerings']),
                inline=False
            )
        pages.append(exploration_embed)
        
        character_embed = discord.Embed(
            colour=0xffffff,
            title=f"Info about {uid}",
            description="Basic character info"
        ).set_footer(
            text="Powered by genshinstats",
            icon_url=GENSHIN_LOGO
        )
        characters = sorted(data['characters'], key=lambda x: x['level'], reverse=True)
        for chunk in grouper(characters, 15):
            embed = character_embed.copy()
            for char in chunk:
                embed.add_field(
                    name=f"{char['name']}",
                    value=f"{'★'*char['rarity']} {self._element_emoji(char['element'])}\nlvl {char['level']}, friendship {char['friendship']}"
                )
            pages.append(embed)
        
        if len(data['teapots']) > 1:
            teapot = data['teapots'][0]
            teapot_embed = discord.Embed(
                colour=0xffffff,
                title=f"Info about {uid}",
                description="Basic teapot info"
            ).set_footer(
                text="Powered by genshinstats",
                icon_url=GENSHIN_LOGO
            ).add_field(
                name="Teapot",
                value=f"Adeptal energy: {teapot['comfort']} (level {teapot['level']})\n"
                      f"Placed items: {teapot['placed_items']}\n"
                      f"Unlocked styles: {', '.join(i['name'] for i in data['teapots'])}"
            )
            pages.append(teapot_embed)
        
        await send_pages(ctx, ctx, pages)
    
    @genshin.command('random')
    @commands.cooldown(5, 60, commands.BucketType.user)
    async def genshin_random(self, ctx: commands.Context):
        """Shows stats for a random user"""
        users = await self.db.users.aggregate([
            {"$sample": {"size": 1}}
        ]).next()
        return await self.genshin(ctx, users['uid'])
    
    @genshin.command('characters')
    @commands.cooldown(5, 60, commands.BucketType.user)
    async def genshin_characters(self, ctx: commands.Context, user: Union[discord.User, int] = None, lang: str = 'en-us'):
        """Shows info about a genshin player's characters"""
        if isinstance(user, int):
            uid = user
        else:
            uid = await self._user_uid(user or ctx.author)
            if uid is None:
                if user is None:
                    await ctx.send(f"Either provide a uid or set your own uid with `{ctx.prefix}genshin setuid`")
                else:
                    await ctx.send(f"User does not have a uid set")
                return
        
        await ctx.trigger_typing()
        try:
            data = await self.get_characters(uid, lang)
        except gs.GenshinStatsException as e:
            await ctx.send(e.msg)
            return

        embeds = [
            discord.Embed(
                colour=_item_color(char['rarity']),
                title=char['name'],
                description=f"{'★'*char['rarity']} {self._element_emoji(char['element'])} "
                            f"level {char['level']} C{char['constellation']}"
            ).set_thumbnail(
                url=char['weapon']['icon']
            ).set_image(
                url=char['icon']
            ).add_field(
                name=f"Weapon",
                value=f"{'★'*char['weapon']['rarity']} {char['weapon']['type']} - {char['weapon']['name']}\n"
                      f"level {char['weapon']['level']} refinement {char['weapon']['refinement']}",
                inline=False
            ).add_field(
                name=f"Artifacts",
                value="\n".join(f"**{(i['pos_name'].title()+':')}** {i['set']['name']}\n{'★'*i['rarity']} lvl {i['level']} - {i['name']}" for i in char['artifacts']) or 'none eqipped',
                inline=False
            ).set_footer(
                text="Powered by genshinstats",
                icon_url=GENSHIN_LOGO
            )
            for char in data
        ]
        await send_pages(ctx, ctx, embeds)
    
    async def _genshin_abyss(self, uid: int, previous: bool) -> list[discord.Embed]:
        """Gets the embeds for spiral abyss history for a specific season."""
        data = await self.get_spiral_abyss(uid, previous)
        if data['stats']['total_battles'] == 0:
            return []
        
        star = self._element_emoji('abyss_star')
        embeds = [
            discord.Embed(
                colour=0xffffff,
                title=f"Spiral abyss info of {uid}",
                description="Overall spiral abyss stats"
            ).add_field(
                name="Stats",
                value=f"Max floor: {data['stats']['max_floor']} Total stars: {data['stats']['total_stars']}\n"
                      f"Total battles: {data['stats']['total_battles']} Total wins: {data['stats']['total_wins']}",
                inline=False
            ).add_field(
                name="Character ranks",
                value="\n".join(f"**{k.replace('_',' ')}**: " + ', '.join(f"{i['name']} ({i['value']})" for i in v[:4]) for k,v in data['character_ranks'].items() if v) or "avalible only for floor 9 or above",
                inline=False
            ).set_author(
                name=f"Season {data['season']} ({data['season_start_time'].replace('-', '/')} - {data['season_end_time'].replace('-', '/')})\n"
            ).set_footer(
                text="Powered by genshinstats",
                icon_url=GENSHIN_LOGO
            ).set_image(
                url=abyss_banners[0]
            )
        ]
        for floor in data['floors']:
            embed = discord.Embed(
                colour=0xffffff,
                title=f"Spiral abyss info of {uid}",
                description=f"Floor **{floor['floor']}** (**{floor['stars']}**{star})",
                timestamp=datetime.fromisoformat(floor['start'])
            ).set_author(
                name=f"Season {data['season']} ({data['season_start_time'].replace('-', '/')} - {data['season_end_time'].replace('-', '/')})\n"
            ).set_footer(
                text="Powered by genshinstats",
                icon_url=GENSHIN_LOGO
            ).set_image(
                url=abyss_banners.get(floor['floor'], discord.Embed.Empty)
            )
            for chamber in floor['chambers']:
                for battle in chamber['battles']:
                    embed.add_field(
                        name=f"Chamber {chamber['chamber']}" + (f"{', 1st' if battle['half']==1 else ', 2nd'} Half " if chamber['has_halves'] else '') + f" ({chamber['stars']}{star})",
                        value='\n'.join(f"{i['name']} (lvl {i['level']})" for i in battle['characters']),
                        inline=True
                    )
                    if battle['half'] == 2:
                        embed.add_field(name='\u200b', value='\u200b')
            embeds.append(embed)
        return embeds
        
    @genshin.command('abyss', aliases=['spiral'])
    @commands.cooldown(5, 60, commands.BucketType.user)
    async def genshin_abyss(self, ctx: commands.Context, uid: Optional[int] = None):
        """Shows info about a genshin player's spiral abyss runs"""
        if uid is None:
            uid = await self._user_uid(ctx.author)
            if uid is None:
                await ctx.send(f"Either provide a uid or set your own uid with `{ctx.prefix}genshin setuid`")
                return
        
        await ctx.trigger_typing()
        # this should've been a generator but it's too much of a pain
        embeds = []
        try:
            embeds += await self._genshin_abyss(uid, False)
            embeds += await self._genshin_abyss(uid, True)
        except gs.GenshinStatsException as e:
            await ctx.send(e.msg)
            return
        if len(embeds) == 0:
            await ctx.send("Player hasn't done any spiral abyss in the past month")
            return
        
        await send_pages(ctx, ctx, embeds)
    
    @genshin.command('wishes', aliases=['wish', 'wishHistory'])
    async def genshin_wish_history(self, ctx: commands.Context):
        """Shows your wish history, to view it you must provide your authkey.
        
        For instructions as to how to get the authkey refer to the "auto import" section in https://paimon.moe/wish.
        Sharing this authkey is safe but if you do not feel comfortable sharing it you should run this command in dms.
        """
        data = await self.db.users.find_one({
            'discord_id': ctx.author.id, 
            'authkey': {'$exists': True}
        })
        if data is None:
            await ctx.send("Please send your authkey to the bot's dms")
            await ctx.author.send("Please send your authkey here: \nFor instructions as to how to get the authkey refer to the \"auto import\" section in https://paimon.moe/wish.")
            message = await discord_input(ctx.bot, ctx.author, ctx.author)
            if message is None:
                await ctx.author.send("Timed out!")
                return
            authkey = message.content
        else:
            authkey = data['authkey']

        while True:
            try:
                uid = await to_thread(gs.get_uid_from_authkey, authkey)
            except gs.InvalidAuthkey:
                await ctx.author.send("That authkey is invalid, it must either be a url with the authkey or the authkey itself.")
            except gs.AuthkeyTimeout:
                await ctx.author.send("Your authkey has expired, please send a new one.")
            else:
                await self.db.users.update_one(
                    {'discord_id': ctx.author.id},
                    {'$set': {'authkey': authkey, 'authkey_expire': datetime.utcnow() + timedelta(days=1)}},
                    upsert=True
                )
                await self.db.users.update_one(
                    {'discord_id': ctx.author.id, 'uid': {'$exists': False}},
                    {'$set': {'uid': uid}}
                )
                break
            message = await discord_input(ctx.bot, ctx.author, ctx.author)
            if message is None:
                await ctx.author.send("Timed out!")
                return
            authkey = message.content

        def embeds():
            """Helper function to make a multiline generator"""
            single_pulls = []
            for time, g in groupby(gs.get_wish_history(authkey=authkey), key=lambda x: x['time']):
                pulls = list(g)
                
                if len(pulls) == 1:
                    single_pulls.append(pulls[0])
                
                if len(single_pulls) == 8 or (len(pulls) == 10 and len(single_pulls) > 0):
                    rarest = max(single_pulls, key=lambda x: x['rarity'])
                    embed = discord.Embed(
                        colour=_item_color(rarest['rarity']),
                        title=f"Wish history of {single_pulls[0]['uid']}", 
                        description=f"{len(single_pulls)} single pulls from various banners",
                        timestamp=datetime.fromisoformat(single_pulls[0]['time'])
                    ).set_footer(
                        text="Powered by genshinstats",
                        icon_url=GENSHIN_LOGO
                    )
                    if rarest['type'] == 'Character':
                        embed.set_thumbnail(url=_character_icon(rarest['name']))
                    elif rarest['id'] in self.icon_cache:
                        embed.set_thumbnail(url=self.icon_cache[rarest['name']])
                    
                    for pull in single_pulls:
                        embed.add_field(
                            name=pull['name'],
                            value=f"{pull['rarity']}★ {pull['type']}\n"
                                  f"Pulled from the **{pull['banner']}**",
                            inline=False
                        )
                    yield embed
                    single_pulls.clear()
                
                if len(pulls) == 10:
                    pulls = sorted(pulls, key=lambda x: (-x['rarity'], x['type']))
                    embed = discord.Embed(
                        colour=_item_color(pulls[0]['rarity']),
                        title=f"Wish history of {pulls[0]['uid']}", 
                        description=f"10-pull from **{pulls[0]['banner']}**",
                        timestamp=datetime.fromisoformat(time)
                    ).set_footer(
                        text="Powered by genshinstats",
                        icon_url=GENSHIN_LOGO
                    )
                    if pulls[0]['type'] == 'Character':
                        embed.set_thumbnail(url=_character_icon(pulls[0]['name']))
                    elif pulls[0]['id'] in self.icon_cache:
                        embed.set_thumbnail(url=self.icon_cache[pulls[0]['id']])
                    
                    for pull in pulls:
                        embed.add_field(
                            name=pull['name'],
                            value=f"{pull['rarity']}★ {pull['type']}\n"
                        )
                    yield embed
        
        await send_pages(ctx, ctx, embeds(), asyncify=True)
    
    @genshin.command('setuid', aliases=['login'])
    async def genshin_setuid(self, ctx: commands.Context, uid: int):
        """Sets a uid to your account letting the bot remember you when you request more data"""
        try:
            await self.get_user_stats(uid)
        except gs.GenshinStatsException as e:
            await ctx.send(e.msg)
            return
        
        await self.db.users.update_one(
            {'discord_id': ctx.author.id},
            {'$set': {'uid': uid}},
            upsert=True
        )
        await ctx.send(f"Updated your uid to {uid}")
        

def setup(bot):
    bot.add_cog(GenshinImpact(bot))
