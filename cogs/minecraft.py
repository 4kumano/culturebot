import asyncio
import re
import socket
from datetime import datetime

import discord
import humanize
from discord.ext import commands, tasks
from mcstatus import MinecraftServer
from utils import CCog, guild_check


class Minecraft(CCog):
    """Status of minecraft servers"""
    gvp_players: dict[str, datetime] = {}
    
    async def init(self):
        self.gvp_server = MinecraftServer.lookup(self.config['gvp'])
        
        await self.bot.wait_until_ready()
        channel = await self.bot.fetch_channel(self.config.getint('gvp_channel'))
        assert isinstance(channel, discord.TextChannel)
        
        async for i in channel.history():
            if i.author == self.bot.user:
                self.gvp_status = i
                break
        else:
            self.gvp_status = await channel.send(embed=discord.Embed(title='status'))
        
        self.update_gvp.start()
    
    async def get_status_embed(self, server: MinecraftServer, gvp: bool = False):
        """Returns a status embed for a minecraft server"""
        try:
            status = await server.async_status()
        except socket.gaierror:
            raise commands.UserInputError(f"The server adress \"{server.host}\" could not be resolved")
        except asyncio.TimeoutError:
            raise commands.CommandError(f"The server {server.host}:{server.port} took too long to respond.")
        except ConnectionError:
            return discord.Embed(
                colour=discord.Colour.red(),
                title=f"Status of {server.host}",
                description="Server is down!",
                timestamp=datetime.now().astimezone()
            )
        
        status.players.sample = status.players.sample or []
        
        if gvp:
            # don't fucking touch this, it's so shit
            for player in self.gvp_players.copy():
                if player not in [p.name for p in status.players.sample]:
                    del self.gvp_players[player]
            
            for player in status.players.sample:
                if player.name not in self.gvp_players:
                    self.gvp_players[player.name] = datetime.now()
                active = datetime.now() - self.gvp_players[player.name]
                player.name += f" - joined {humanize.naturaldelta(active)} ago"
        
        return discord.Embed(
            colour=0x00AA00,
            title=f"Status of {server.host}",
            description=re.sub('§.', '', status.description),
            timestamp=datetime.now().astimezone()
        ).add_field(
            name=f"{status.players.online} / {status.players.max} players",
            value='\n'.join(i.name for i in status.players.sample) or '\u200b'
        ).set_footer(
            text=f"Latency: {status.latency}ms | Version: {status.version.name}"
        )
    
    @commands.command()
    async def mcstatus(self, ctx: commands.Context, adress: str):
        """Shows the status of a minecraft server"""
        server = MinecraftServer.lookup(adress)
        embed = await self.get_status_embed(server)
        await ctx.send(embed=embed)
    
    @commands.command()
    @guild_check(790498180504485918)
    async def gvp(self, ctx: commands.Context):
        """Shows the status of the gvp minecraft server"""
        embed = await self.get_status_embed(self.gvp_server, gvp=True)
        await ctx.send(embed=embed)
    
    @tasks.loop(seconds=30, reconnect=True)
    async def update_gvp(self):
        try:
            embed = await self.get_status_embed(self.gvp_server, gvp=True)
        except Exception as e:
            self.logger.error(e)
            await asyncio.sleep(300)
        else:
            await self.gvp_status.edit(embed=embed)

def setup(bot):
    bot.add_cog(Minecraft(bot))
