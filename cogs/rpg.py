from __future__ import annotations
import asyncio

import discord
from discord import Message
from discord.ext import commands
from discord.ext.commands import Bot, Context
from pretty_help import DefaultMenu
from utils import discord_choice, multiline_join, wrap

from ._rpg import Entity, Hero, heroes

TUTORIAL = {
    'basics': {
        'concept': """
            Your task is to kill all the enemies you encounter in a dungeon.
            You will be prompted to choose a move and the enemy will move at the same time.
            Every time you defeat an enemy you gain exp which will let you upgrade your stats.
            At the start you can choose a class which will give you special moves.
        """,
        'gameplay': """
            You will be defeating a horde of individual enemies one by one.
            Every enemy has its own stats and gives xp based on them.
            Every 3 enemies you will face a boss which has a special move but it gives more xp.
            Once you defeat all bosses you willlbl enter endless mode.
        """
    },
    'fighting': {
        'turns': """
            Every turn both you and your opponnet choose moves at the same time.
            You can pick one of 3 moves: attack ⚔️, defend 🛡️ and rest 🔋.
            There's also a special move which needs to be charged ⚡ and then unleashed ✨.
            You cannot use 3 of the same moves after each-other.
        """,
        'attack ⚔️': "Deals damage based on your strength, consumes two stamina.",
        'defend 🛡️': "Defends against an opponent's attack, consumes one stamina.",
        'rest 🔋': "Rests and recharges your stamina, however you will be vulnerable to attacks.",
        'charge ⚡': "Charges your special ability.",
        'special ✨': "Uses your special ability."
    },
    # 'heroes':{
    #     'knight':"idk",
    #     'rogue':"idk",
    #     'viking':"idk"
    # }
}

command_help = '⚔️ attack | 🛡️ defend | 🔋 rest | ⚡ charge | ✨ special'


class RPG(commands.Cog, name='rpg'):
    """A rogue-like rpg game"""

    def __init__(self, bot: Bot):
        self.bot = bot
        self.menu = DefaultMenu()
    
    async def update_table(self, msg: Message, message: str, *entities: Entity, instructions: bool = True):
        """Updates the table in a message object."""
        table = multiline_join([i.table for i in entities], sep=' '*6, prefix=' '*8)
        if command_help:
            table = command_help+'\n' + table
        await msg.edit(content=wrap(message + table))

    async def gameloop(self, ctx: Context, hero: Hero, difficulty: int):
        while hero.hp > 0:
            enemy = hero.get_next_enemy()
            msg = await ctx.send(wrap(f'Now fighting {enemy}'))
            await asyncio.sleep(1)
            message = ''

            while hero.hp > 0 and enemy.hp > 0:
                await self.update_table(msg, message, hero, enemy, instructions=True)
                
                move = await discord_choice(
                    self.bot, msg, ctx.author,
                    hero.possible_moves,
                    delete_after_timeout=True
                )
                if move is None:
                    await ctx.send('TIMEOUT')
                    return
                enemy_move = enemy.decide_move(hero, difficulty)

                enemy.determine_move(enemy_move, hero, move)
                message = hero.determine_move(move, enemy, enemy_move) + '\n'

            await self.update_table(msg, message, hero, enemy, instructions=False)

            if hero.hp < 0:
                await ctx.send(f'You have been defeated by the {enemy}')
                break

            await ctx.send(f'You have defeated the {enemy}')
            hero.end_fight(enemy)

        await ctx.send('Game Over!')

    @commands.group('rpg', aliases=['game', 'play'], invoke_without_command=True)
    async def rpg(self, ctx: Context):
        """A rouge-like rpg game you can play with reactions.

        To get the tutorial use the "tutorial" or "rpg tutorial" commands.
        """
        await ctx.send("Welcome to culturebot's rpg game! If this is your first time playing make sure to read the tutorial\n", delete_after=10)

        msg = await ctx.send(wrap(
            'Please pick a hero:\n'
            "knight ⚔️ | bleed, makes the enemy lose stamina\n"
            "rogue  🗡️ | dodge, dodge enemy attack\n"
            "viking 🪓 | punch, deal high damage"))
        choice = await discord_choice(
            self.bot, msg, ctx.author,
            dict(zip(['⚔️', '🗡️', '🪓'], heroes))
        )
        if choice is None:
            return
        hero = Hero(**choice)
        await msg.edit(content=wrap(
            'Please pick a difficulty:\n'
            "1: easy   🟩 | enemies move basically at random, gets boring after a while.\n"
            "2: normal 🟨 | enemies use simple AI to attack, recomended for casual players.\n"
            "3: hard   🟥 | super smart AI, hard to beat, a true challenge."))
        difficulty = await discord_choice(
            self.bot, msg, ctx.author,
            dict(zip(['🟩', '🟨', '🟥'], [1, 2, 3]))
        )
        if difficulty is None:
            return
        await msg.edit(content=f"Now playing as {hero.name} on {['dev','easy','normal','hard'][difficulty]}")

        await self.gameloop(ctx, hero, difficulty)

    @rpg.command('tutorial', aliases=['help', 'rpghelp'])
    async def tutorial(self, ctx: Context):
        """An interactive tutorial for the rpg game."""
        embeds = []
        for category, entries in TUTORIAL.items():
            embed = discord.Embed(
                title=category
            ).set_author(
                name='rpg tutorial',
                icon_url="https://icons.iconarchive.com/icons/google/noto-emoji-objects/1024/62963-crossed-swords-icon.png"
            ).set_footer(
                text="Navigate the tutorial using the buttons below."
            )
            for name, value in entries.items():
                embed.add_field(name=name, value=value, inline=False)
            embeds.append(embed)

        await self.menu.send_pages(ctx, ctx.channel, embeds)

    @commands.command('tutorial', aliases=['rpghelp'])
    async def invoke_tutorial(self, ctx: Context):
        """An interactive tutorial for the rpg game.

        Shortcut for "rpg tutorial"
        """
        await self.tutorial(ctx)


def setup(bot):
    bot.add_cog(RPG(bot))
