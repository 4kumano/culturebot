import discord
from discord.channel import TextChannel
from discord.ext import commands
from discord.ext.commands import Context
from discord.member import Member
from discord.message import Message

from utils import CCog


class BB(CCog, name="Belle's Battleground"):
    """Commands for Belle's Battlegorund"""

    guild_id = 842788736008978504

    async def init(self):
        await self.bot.wait_until_ready()
        c = await self.bot.fetch_channel(858832337277288459)
        assert isinstance(c, discord.CategoryChannel)
        self.links_category = c

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        """Basically just aura"""
        if message.guild is None or message.guild.id != self.guild_id :
            return
        
        if message.mentions and any(i in message.content.lower() for i in ("thanks", "thank you")):
            await message.add_reaction("👍")
            await message.add_reaction("❌")

    @commands.group(invoke_without_command=True)
    @commands.check(lambda ctx: bool(ctx.guild and ctx.guild.id == 842788736008978504))
    async def bb(self, ctx: Context):
        """Manages links on Belle's Battleground"""
        await ctx.send("Please either `add` or `remove` a link")

    @bb.command("add", aliases=["edit"])
    async def bb_add(self, ctx: Context, member: Member, link: str):
        """Adds a link"""
        if "github" in link:
            channel = discord.utils.get(self.links_category.channels, name="github")
        elif "anilist" in link:
            channel = discord.utils.get(self.links_category.channels, name="anilist")
        else:
            raise commands.UserInputError("Link is not valid")
        assert isinstance(channel, discord.TextChannel)
        
        async for message in channel.history():
            if member in message.mentions:
                if message.author != self.bot.user:
                    await message.delete()
                    message = await channel.send("dummy")
                await message.edit(content=f"{member.mention} - {link}")
                await ctx.send(f"Edited {member}'s {channel.name} link")
                break
        else:
            await channel.send(f"{member.mention} - {link}", allowed_mentions=discord.AllowedMentions.none())
            await ctx.send(f"Added {member}'s {channel.name} link")

    @bb.command("remove")
    async def bb_remove(self, ctx: Context, member: Member, channel: TextChannel):
        """Removes a link"""
        async for message in channel.history():
            if member in message.mentions:
                break
        else:
            await ctx.send(f"{member} doesn't have a link in {channel}")
            return
        await message.delete()
        await ctx.send(f"Deleted {member}'s {channel.name} link")


def setup(bot):
    bot.add_cog(BB(bot))
