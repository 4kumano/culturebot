from __future__ import annotations
import asyncio
import dislash
import discord
from discord.ext import commands
from utils import CCog
import utils


class Slash(CCog):
    """Rando slash commands"""
    @dislash.slash_command(
        description="Shows the bot's latency",
        options=[],
        connectors=None
    )
    async def ping(self, inter: dislash.SlashInteraction):
        """Short help"""
        await inter.reply(f"Pong! :ping_pong: ({self.bot.latency*1000:.2f}ms)")
    
    
    @dislash.slash_command(
        description="Gets the anime soure using trace.moe",
        options=[
            dislash.Option("image", "url link to the image/gif", type=dislash.OptionType.STRING, required=True)
        ],
        connectors=None
    )
    async def tracemoe(self, inter: dislash.SlashInteraction, image: str):
        asyncio.create_task(inter.reply(type=5))
        r = await self.bot.session.get("https://api.trace.moe/search", params={'url': image, 'anilistInfo': ''})
        data = await r.json()
        if data['error']:
            await inter.reply(data['error'])
            return
        
        embeds = [
            discord.Embed(
                colour=0x2ecc71,
                title=f"{result['anilist']['title']['romaji']} episode {result['episode']}",
                url=f"https://anilist.co/anime/{result['anilist']['id']}",
                description=f"from {result['from']//60:.0f}:{result['from']%60:.0f} to {result['to']//60:.0f}:{result['to']%60:.0f}\n\nsimilarity {result['similarity']:.2%}",
            ).set_image(
                url=result['image'] + '&size=l'
            ).set_footer(
                text=f"{result['filename']}"
            )
            for result in data['result']
        ]
        await inter.edit(embed=embeds[0])
    
    @staticmethod
    def _get_title(data):
        # Order is important!
        if 'title' in data:
            return data['title']
        elif 'eng_name' in data:
            return data['eng_name']
        elif 'material' in data:
            return data['material']
        elif 'source' in data:
            return data['source']
        elif 'created_at' in data:
            return data['created_at']

    
    @dislash.slash_command(
        description="Gets the sauce of an image using saucenao",
        options=[
            dislash.Option("image", "url link to the image/gif", type=dislash.OptionType.STRING, required=True),
            dislash.Option("results", "the amount of results", type=dislash.OptionType.INTEGER),
            dislash.Option("min_similarity", "minimum similarity needed to show the image", type=dislash.OptionType.NUMBER),
        ],
        connectors=None
    )
    async def saucenao(self, inter: dislash.SlashInteraction, image: str, results: int = 3, min_similarity: float = 70):
        asyncio.create_task(inter.reply(type=5))
        key = self.bot.config.get('misc', 'saucenao_key')
        print(key)
        r = await self.bot.session.get(
            "https://saucenao.com/search.php",
            params={'output_type': 2, 'numres': results, 'url': image, 'api_key': key},
        )
        if r.status != 200:
            await inter.edit("Unknown error occured")
            self.logger.error(await r.text())
            return

        data = await r.json()
        if data['header']['status'] != 0:
            await inter.edit(data['header']['message'])
            return
        
        from pprint import pprint
        pprint(data['results'])
        
        embeds = [
            discord.Embed(
                colour=0x2ecc71,
                title=f"{self._get_title(result['data'])}",
                url=(result['data']['ext_urls'][0] if 'ext_urls' in result['data'] else 
                     f'http://www.getchu.com/soft.phtml?id={data["getchu_id"]}' if 'getchu_id' in result['data'] else
                     discord.Embed.Empty),
                description="\n".join(
                    f"{' '.join(i.title() for i in k.split('_'))}: {', '.join(v) if isinstance(v, list) else v}" 
                    for k, v in result['data'].items()
                    if k not in {'title', 'ext_urls'}
                ),
            ).set_image(
                url=result['header']['thumbnail']
            ).set_footer(
                text=f"similarity {float(result['header']['similarity']):.2f}%"
            )
            for result in data['results']
            if float(result['header']['similarity']) >= min_similarity
        ]
        if len(embeds) == 0:
            await inter.edit("No similar results found")
            return
        
        await inter.edit(embeds=embeds)

def setup(bot):
    bot.add_cog(Slash(bot))
