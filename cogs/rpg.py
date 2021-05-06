from __future__ import annotations

import json, asyncio
import random
from copy import deepcopy
from enum import Enum
from typing import Iterable, List, Optional, Type, TypeVar, Union

import discord
from discord import TextChannel, Message, User
from discord.ext import commands
from discord.ext.commands import Bot, Context
from pretty_help import DefaultMenu

T = TypeVar('T')

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


with open('assets/rpg.json') as file:
    rpg_data: dict[str,list[dict]] = json.load(file)
heroes = rpg_data['heroes']
enemies = rpg_data['enemies']
bosses = rpg_data['bosses']


def multiline_join(strings: list[str], sep='') -> str:
    """Like str.join but multiline."""
    parts = zip(*(str(i).splitlines() for i in strings))
    return '\n'.join(sep.join(i) for i in parts)

async def discord_choice(
    bot: Bot, message: Message, user: User, 
    choices: Union[dict[str,T],list[T]], 
    timeout: float=60, delete_after_timeout: bool=True,
    cancel: Optional[str]='❌'
) -> Optional[T]:
    """Creates a discord reaction choice
    
    Takes in a bot to wait with, a message to add reactions to and a user to wait for.
    Choices must either be a dict of emojis to choices or an iterable of emojis.
    If the items of iterable have a `value` attribute that will be the emoji.
    
    If cancel is set to None, the user will not be able to cancel.
    """ 
    if isinstance(choices,dict):
        reactions = choices
    else:
        reactions = {getattr(i,'value',str(i)).strip():i for i in choices}
    
    for i in reactions:
        await message.add_reaction(i)
    if cancel:
        await message.add_reaction(cancel)
    
    try:
        reaction,_ = await bot.wait_for(
            'reaction_add', 
            check=lambda r,u: (str(r) in reactions or str(r)==cancel) and u == user, 
            timeout=timeout
        )
    except asyncio.TimeoutError:
        if delete_after_timeout:
            await message.delete()
        return None
    finally:
        await message.clear_reactions()
    
    if str(reaction) == cancel:
        if delete_after_timeout:
            await message.delete()
        return None
    
    return reactions[str(reaction)]


class Move(Enum):
    ATTACK = '⚔️'
    DEFEND = '🛡️'
    REST = '🔋'
    CHARGE = '⚡'
    SPECIAL = '✨'

class Entity:
    """Base RPG Entity"""
    # entity info
    type: str = 'null'
    name: str
    # base stats
    strength: int
    health: int
    stamina: int
    # current stats
    hp: int
    st: int
    move_history: list[Move] = []
    # special
    level: int = 0
    special: Optional[str] = None
    special_level: int = 1
    charged: bool = False

    def __init__(self, **kwargs):
        """Sets entity attributes"""
        self.type = type(self).__name__.lower()
        self.__dict__.update(kwargs)
        
        self.hp = self.health
        self.st = self.stamina
    
    def __str__(self) -> str:
        return self.name
    
    @property
    def table(self) -> str:
        """Returns a pretty table with an entity's stats
        
        ```
        +-------+-------+
        | ?? hp | ?? st |
        +-------+-------+
        | ????????????? |
        +----------+----+
        | strength | ?? |
        +----------+----+
        | health   | ?? |
        +----------+----+
        | stamina  | ?? |
        +----------+----+
        lvl ??   charged! 
        ```
        """
        return (
        f"+-------+-------+\n"
        f"| {self.hp:2} hp | {self.st:2} st |\n"
        f"+-------+-------+\n"
        f"|{self.name:^15}|\n"
        f"+----------+----+\n"
        f"| strength | {self.strength:^2} |\n"
        f"+----------+----+\n"
        f"| health   | {self.health:^2} |\n"
        f"+----------+----+\n"
        f"| stamina  | {self.stamina:^2} |\n"
        f"+----------+----+\n"
        f"lvl {self.level:<2}   {'charged!' if self.charged else ' '*8}")

    def __repr__(self) -> str:
        return f"{type(self).__name__}({', '.join(f'{k}={v!r}' for k,v in self.__dict__.items())})"
    
    def copy(self):
        return deepcopy(self)

    def use_special(self, other: Move):
        """Uses a special move."""
        if self.special is None:
            raise ValueError("Entity does not have a special move.")
        if not self.charged:
            raise ValueError("Special move is not charged.")

        raise NotImplementedError
    
    @property
    def last_move(self) -> Move:
        return self.move_history[-1]

    @property
    def _moves(self) -> list[Move]:
        moves = [Move.ATTACK, Move.DEFEND, Move.REST]
        if self.special is not None:
            moves.append(Move.SPECIAL if self.charged else Move.CHARGE)
        return moves
    
    @property
    def possible_moves(self) -> list[Move]:
        """A list of possible moves."""
        moves = self._moves
        if len(self.move_history) >= 2 and self.move_history[-1] == self.move_history[-2]:
            moves.remove(self.move_history[-1])
        return moves

class Hero(Entity):
    """Base Hero class"""
    strength = 2
    health = 4
    stamina = 4
    level = 0
    
    defeated: int = 0
    undefeated_bosses: List[Boss]

    def __init__(self, name: str, special: Optional[str]):
        self.name = name
        self.special = special
        self.undefeated_bosses = [Boss(**i) for i in bosses]
        super().__init__()
    
    def get_next_enemy(self) -> Type[Enemy]:
        """Gets the next appropriate enemy based on defeat count"""
        return Enemy(**random.choice(enemies))
    
        
    
class Enemy(Entity):
    """Base Enemy class"""
    def __init__(self, name: str, **kwargs):
        self.name = name
        super().__init__(**kwargs)
    
    def decide_move(self, hero: Hero, difficulty: int = 1) -> Move:
        if difficulty == 1:
            # rest if not enough energy to attack
            if self.st <= 1:
                return Move.REST
            elif self.special and self.charged:
                return Move.SPECIAL
            else:
                moves = set(self._moves) - {self.last_move}
                return random.choice(moves)
                

class Boss(Enemy):
    """Base Boss class"""
    
    def __init__(self, name: str, special: str, **kwargs):
        self.special = special
        super().__init__(name, **kwargs)


def determine_moves(a: Entity, b: Entity, movea: Move, moveb: Move) -> str:
    """Determines move output and returns a str message"""
    for entity,move in zip([a,b],[movea,moveb]):
        if move == Move.ATTACK:
            entity.st -= 2
        elif move == Move.DEFEND:
            entity.st -= 1
        elif move == Move.REST:
            entity.st = entity.stamina
        elif move == Move.CHARGE:
            entity.charged = True
    
    if movea == Move.ATTACK:
        if moveb == Move.ATTACK:
            a.hp -= b.strength // 2
            b.hp -= a.strength // 2
            return f"Both {a} and {b} have attacked"
        elif moveb == Move.DEFEND:
            return f"{a}'s attack was defended by {b}"
        elif moveb == Move.SPECIAL:
            raise NotImplementedError
        else:
            return f"{a} has attacked while {b} was {'running away' if move == Move.RUN else 'charging'}"
            
        


class RPG(commands.Cog, name='rpg'):
    """A rogue-like rpg game"""

    def __init__(self, bot: Bot):
        self.bot = bot
        self.menu = DefaultMenu()
        
    async def gameloop(self, ctx: Context, hero: Hero, difficulty: int):
        while True:
            enemy = hero.get_next_enemy()
            while True:
                table = multiline_join([hero.table,enemy.table],' '*6)
                await ctx.send(table)
                
            break

    @commands.group('rpg', aliases=['game', 'play'], invoke_without_command=True)
    async def rpg(self, ctx: Context):
        """A rouge-like rpg game you can play with reactions.

        To get the tutorial use the "tutorial" or "rpg tutorial" commands.
        """
        await ctx.send("Welcome to culturebot's rpg game! If this is your first time playing make sure to read the tutorial\n", delete_after=10)
        
        msg = await ctx.send('```Please pick a hero:\n'
            "knight ⚔️ | bleed, do damage every turn\n"
            "rogue  🗡️ | dodge, dodge enemy attack\n"
            "viking 🪓 | punch, deal high damage\n```")
        choice = await discord_choice(
            self.bot, msg, ctx.author, 
            dict(zip(['⚔️','🗡️','🪓'], heroes))
        )
        if choice is None:
            return
        hero = Hero(**choice)
        await msg.edit(content='```Please pick a difficulty:\n'
            "1: easy   🟩 | enemies move basically at random, gets boring after a while.\n"
            "2: normal 🟨 | enemies use simple AI to attack, recomended for casual players.\n"
            "3: hard   🟥 | super smart AI, hard to beat, a true challenge.```")
        difficulty = await discord_choice(
            self.bot, msg, ctx.author, 
            dict(zip(['🟩','🟨','🟥'],[1,2,3]))
        )
        if choice is None:
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
