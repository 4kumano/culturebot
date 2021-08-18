from typing import Any, Optional, TYPE_CHECKING, Counter

from fastapi import FastAPI, Response, Query, WebSocket
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

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
    rank: int = 1
    swear: str = "fuck"
    amount: int

class SwearMember(BaseModel):
    rank: int = 1
    member: int = 803268588387434536
    member_name: Optional[str] = "Culture bot#7920"
    swears: list[Swear]
    total: int

@app.get("/swears/{guild}", tags=['swears'], summary="guild swears", response_model=list[SwearMember])
async def guild_swears(guild: int, limit: int = Query(10, lt=50)):
    """A leaderboard of swears for a server"""
    # there is a proper way to do this but I can't be fucked.
    swears: list[tuple[int, dict[str, int]]] = [
        (doc["member"], doc["swears"]) async for doc in app.bot.db.culturebot.swears.find({"guild": guild}).limit(limit)
    ]
    # we have to sort in python
    swears.sort(key=lambda x: sum(x[1].values()), reverse=True)
    return [
        {
            "rank": rank,
            "member": member,
            "member_name": str(app.bot.get_user(member)),
            "swears": [{"rank": srank, "swear": swear, "amount": amount} for srank, (swear, amount) in enumerate(Counter(swears).most_common(), 1)],
            "total": sum(swears.values()),
        }
        for rank, (member, swears) in enumerate(swears, 1)
    ]


@app.get("/swears/{guild}/{member}", tags=['swears'], summary="member swears", response_model=list[Swear])
async def member_swears(guild: int, member: int):
    """A leaderboard of swears for a server member"""
    swears = await app.bot.db.culturebot.swears.find_one({"member": int(member), "guild": guild})
    c = Counter(swears["swears"])
    return [{"rank": rank, "swear": swear, "amount": amount} for rank, (swear, amount) in enumerate(c.most_common(), 1)]
