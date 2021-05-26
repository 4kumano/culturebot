from __future__ import annotations

import json
import random
from copy import deepcopy
from enum import Enum
from typing import List, Optional

with open('assets/rpg.json') as file:
    rpg_data: dict[str, list[dict]] = json.load(file)
heroes = rpg_data['heroes']
enemies = rpg_data['enemies']
bosses = rpg_data['bosses']


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
    move_history: list[Move]
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

        self.move_history = []

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

    def use_special(self, op: Entity, opmove: Move) -> str:
        """Uses a special move."""
        if not self.charged:
            raise ValueError("Special move is not charged.")

        if self.special is None:
            raise ValueError("Entity does not have a special move.")
        elif self.special == 'bleed':
            take_st = min(self.special_level, op.stamina)
            op.stamina -= take_st
            self.health += take_st - 1
        # elif self.special == 'dodge':
        #     if 
        
        return ''

    @property
    def last_move(self) -> Optional[Move]:
        return self.move_history[-1] if self.move_history else None

    @property
    def possible_moves(self) -> list[Move]:
        """A list of possible moves."""
        moves = []
        if self.st >= 2:
            moves.append(Move.ATTACK)
        if self.st >= 1:
            moves.append(Move.DEFEND)
        moves.append(Move.REST)

        if self.special is not None:
            moves.append(Move.SPECIAL if self.charged else Move.CHARGE)

        if (len(self.move_history) >= 2 and
            self.move_history[-1] == self.move_history[-2] and
            self.move_history[-1] in moves
        ):
            moves.remove(self.move_history[-1])
        return moves

    def determine_move(self, move: Move, op: Entity, opmove: Move) -> str:
        """Determines move output and return a string message.

        Takes in the move, the opponent and the opponent's move.
        """
        self.move_history.append(move)

        if move == Move.ATTACK:
            self.st -= 2
            if opmove == Move.ATTACK:
                op.hp -= self.strength // 2
                return f"Both {self} and {op} have attacked."
            elif opmove == Move.DEFEND:
                return f"{self}'s attack was defended by {op}"
            else:
                op.hp -= self.strength
        elif move == Move.DEFEND:
            self.st -= 1
        elif move == Move.REST:
            self.st = self.stamina
        elif move == Move.CHARGE:
            self.charged = True
        elif move == Move.SPECIAL:
            self.use_special(op, opmove)

        past_tense_move = {
            Move.ATTACK: 'attacked',
            Move.DEFEND: 'defended',
            Move.REST: 'rested',
            Move.CHARGE: 'charged',
            Move.SPECIAL: 'used their special'
        }[move]
        if move == opmove:
            return f"Both {self} and {op} have {past_tense_move}"
        elif move == Move.ATTACK and opmove == Move.DEFEND:
            return f"{op} has defended {self}'s attack"
        elif move == Move.DEFEND and opmove == Move.ATTACK:
            return f"{self} has defended {op}'s attack"
        else:
            continous_tense_move = {
                Move.ATTACK: 'attacking',
                Move.DEFEND: 'defending',
                Move.REST: 'resting',
                Move.CHARGE: 'charging',
                Move.SPECIAL: f'using their special "{op.special}"'
            }[opmove]
            return f"{self} has {past_tense_move} while {op} was {continous_tense_move}"


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

    def get_next_enemy(self) -> Enemy:
        """Gets the next appropriate enemy based on defeat count"""
        return Enemy(**random.choice(enemies))
    
    def end_fight(self, enemy: Entity = None):
        """Ends fight with an opponent.
        
        This incrememnts counters, clears move history 
        and restores hp and stamina.
        """
        self.defeated += 1
        self.move_history.clear()
        if enemy in self.undefeated_bosses:
            self.undefeated_bosses.remove(enemy)
        
        if isinstance(enemy, Enemy):
            self.st = self.stamina
            if self.undefeated_bosses:
                self.hp = self.health
            else: # when in endless mode only half the health is restored
                self.hp = min(self.hp + self.health//2, self.health)
            


class Enemy(Entity):
    """Base Enemy class"""
    def __init__(self, name: str, **kwargs):
        self.name = name
        super().__init__(**kwargs)

    def decide_move(self, hero: Hero, difficulty: int = 1) -> Move:
        if difficulty == 1:
            # rest if not enough energy to attack
            if self.st == 0:
                return Move.REST
            # elif self.special and self.charged:
            #     return Move.SPECIAL
            else:
                return random.choice(self.possible_moves)
        raise NotImplementedError


class Boss(Enemy):
    """Base Boss class"""
    def __init__(self, name: str, special: str, **kwargs):
        self.special = special
        super().__init__(name, **kwargs)
