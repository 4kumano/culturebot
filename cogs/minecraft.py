import asyncio
import socket
from datetime import datetime

import discord
from discord.channel import TextChannel
from discord.ext import commands, tasks
from discord.ext.commands import Bot, Context
from mcstatus import MinecraftServer
from utils import CCog


class Minecraft(CCog):
    """Short description"""
    def __init__(self, bot: Bot):
        self.bot = bot
        self.gvp_server = MinecraftServer.lookup(self.config['gvp'])
    
    @commands.Cog.listener()
    async def on_ready(self):
        channel = await self.bot.fetch_channel(self.config.getint('gvp_channel'))
        assert isinstance(channel, TextChannel)
        
        async for i in channel.history():
            if i.author == self.bot.user:
                self.gvp_status = i
                break
        else:
            self.gvp_status = await channel.send(embed=discord.Embed(title='status'))
        
        self.update_gvp.start()
    
    async def get_status_embed(self, server: MinecraftServer):
        """Returns a status embed for a minecraft server"""
        try:
            status = await server.async_status()
        except socket.gaierror:
            raise commands.UserInputError(f"The server adress \"{server.host}\" could not be resolved")
        except asyncio.TimeoutError:
            raise commands.CommandError("The server took too long to respond.")
        except ConnectionError:
            return discord.Embed(
                colour=discord.Colour.red(),
                title=f"Status of {server.host}",
                description="Server is down!",
                timestamp=datetime.now().astimezone()
            )
            
        return discord.Embed(
            colour=0x00AA00,
            title=f"Status of {server.host}",
            description=status.description['text'],
            timestamp=datetime.now().astimezone()
        ).set_thumbnail(
            url=status.favicon or discord.Embed.Empty
        ).add_field(
            name=f"{status.players.online} / {status.players.max} players",
            value=' | '.join(i.name for i in status.players.sample or []) or '\u200b'
        ).set_footer(
            text=f"Latency: {status.latency}ms | Version: {status.version.name}"
        )
    
    @commands.command()
    async def mcstatus(self, ctx: Context, adress: str):
        """Shows the status of a minecraft server"""
        server = MinecraftServer.lookup(adress)
        embed = await self.get_status_embed(server)
        await ctx.send(embed=embed)
    
    @commands.command()
    async def gvp(self, ctx: Context):
        """Shows the status of the gvp minecraft server"""
        embed = await self.get_status_embed(self.gvp_server)
        await ctx.send(embed=embed)
    
    @commands.command()
    async def mcping(self, ctx: Context, adress: str):
        """Shows the ping of a minecraft server"""
        server = MinecraftServer.lookup(adress)
        try:
            ping = await server.async_ping()
        except:
            await ctx.send('Invalid server adress')
            return
        await ctx.send(f"{ping}ms")
    
    @tasks.loop(seconds=30)
    async def update_gvp(self):
        embed = await self.get_status_embed(self.gvp_server)
        await self.gvp_status.edit(embed=embed)

def setup(bot):
    bot.add_cog(Minecraft(bot))
