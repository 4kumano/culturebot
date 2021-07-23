import traceback
from typing import TYPE_CHECKING, Counter, Optional, TypedDict

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

if TYPE_CHECKING:
    from bot import CBot

class CApp(FastAPI):
    """An app that provides a reference to the bot singleton"""
    bot: 'CBot'
    def __new__(cls):
        # __new__ as to not accidentally overwrite the __init__ annotations
        from bot import bot
        self = super().__new__(cls)
        self.bot = bot
        return self
    

app = CApp()

@app.get('/genshin', deprecated=True)
def genshin():
    """Deprecated resource for getting genshin info of a user"""
    return RedirectResponse(
        "https://github.com/thesadru/genshinstats", 
        status_code=308
    )

@app.get('/stats')
def stats():
    """Discord stats of the bot."""
    bot = app.bot
    return {
        'total_guilds': len(bot.guilds),
        'total_members': sum(guild.member_count for guild in bot.guilds),
        'uptime': bot.uptime.total_seconds()
    }

class SwearsGuild(BaseModel):
    rank: int
    member: int
    swears: int
@app.get('/swears/{guild}', response_model=list[SwearsGuild])
async def swears(guild: int):
    """A leaderboard of swears for a server"""
    # server stats
    c: Counter[int] = Counter()
    async for doc in app.bot.db.culturebot.swears.find({'guild': guild}):
        c[doc['member']] += sum(doc['swears'].values())
    return [
        {
            'rank': rank,
            'member': member,
            'swears': amount
        }
        for rank, (member, amount) in enumerate(c.most_common(10), 1)
    ]

class SwearsMember(BaseModel):
    rank: int
    swear: str
    amount: int
@app.get('/swears/{guild}/{member}', response_model=list[SwearsMember])
async def swears_m(guild: int, member: int):
    """A leaderboard of swears for a server member"""
    # guild stats
    swears = await app.bot.db.culturebot.swears.find_one(
        {'member': int(member), 'guild': guild}
    )
    c = Counter(swears['swears'])
    return [
        {
            'rank': rank,
            'swear': swear,
            'amount': amount
        }
        for rank, (swear, amount) in enumerate(c.most_common(10), 1)
    ]

@app.exception_handler(Exception)
def handle_internal_error(exception: Exception):
    traceback.print_exception(type(exception), exception, exception.__traceback__)
