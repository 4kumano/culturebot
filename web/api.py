from typing import Any, Optional, TYPE_CHECKING, Counter

from fastapi import FastAPI, Response, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from bot import CBot


class CAppMeta(type):
    def __new__(cls, name: str, bases: tuple[type, ...], attrs: dict[str, Any]):
        from bot import bot

        attrs["bot"] = bot
        return super().__new__(cls, name, bases, attrs)

class CApp(FastAPI, metaclass=CAppMeta):
    """An app that provides a reference to the bot singleton"""
    bot: "CBot"

def _get_user_name(id: int) -> Optional[str]:
    user = app.bot.get_user(id)
    return str(user) if user else None

app = CApp()


@app.get("/", include_in_schema=False)
def index():
    return RedirectResponse("./docs")


@app.get("/test/{status_code}", include_in_schema=False)
def test(status_code: str):
    return Response(status_code=int(status_code))


@app.get("/genshin", deprecated=True)
def genshin():
    """Deprecated resource for getting genshin info of a user"""
    return RedirectResponse("https://github.com/thesadru/genshinstats", status_code=308)


@app.get("/stats", summary="bot stats", response_model=dict)
def stats():
    """Discord stats of the bot."""
    bot = app.bot
    return {
        "total_guilds": len(bot.guilds),
        "total_members": sum(guild.member_count for guild in bot.guilds),
        "uptime": bot.uptime.total_seconds(),
    }


class Swear(BaseModel):
    rank: int
    swear: str = Field(example="fuck")
    amount: int

class SwearMember(BaseModel):
    rank: int
    member: int = Field(example=803268588387434536)
    member_name: Optional[str] = Field(None, example="Culture bot#7920")
    swears: list[Swear]
    total: int

@app.get("/swears/{guild}", tags=['swears'], summary="guild swears", response_model=list[SwearMember])
async def guild_swears(guild: int, limit: int = Query(10, lt=50)):
    """A leaderboard of swears for a server"""
    # there is a proper way to do this but I can't be fucked.
    swears = [doc async for doc in app.bot.db.culturebot.swears.find({"guild": guild}).sort('total', -1).limit(limit)]
    return [
        {
            "rank": rank,
            "member": doc['member'],
            "member_name": _get_user_name(doc['member']),
            "swears": [{"rank": srank, "swear": swear, "amount": amount} for srank, (swear, amount) in enumerate(Counter(doc['swears']).most_common(), 1)],
            "total": doc['total'],
        }
        for rank, doc in enumerate(swears, 1)
    ]


@app.get("/swears/{guild}/{member}", tags=['swears'], summary="member swears", response_model=list[Swear])
async def member_swears(guild: int, member: int):
    """A leaderboard of swears for a server member"""
    swears = await app.bot.db.culturebot.swears.find_one({"member": member, "guild": guild})
    return [{"rank": rank, "swear": swear, "amount": amount} for rank, (swear, amount) in enumerate(Counter(swears["swears"]).most_common(), 1)]


class XPLeaderboard(BaseModel):
    rank: int
    member: int = Field(example=803268588387434536)
    member_name: Optional[str] = Field(None, example="Culture bot#7920")
    xp: int

@app.get('/xp/{guild}', tags=['xp'], summary="guild xp leaderboard", response_model=list[XPLeaderboard])
async def guild_xp(guild: int, limit: int = Query(10, lt=50)):
    xp = [doc async for doc in app.bot.db.xp.xp.find({"guild": guild}).sort('xp', -1).limit(limit)]
    return [
        {
            "rank": rank,
            "member": doc['member'],
            "member_name": _get_user_name(doc['member']),
            "xp": doc["xp"]
        }
        for rank, doc in enumerate(xp, 1)
    ]
    