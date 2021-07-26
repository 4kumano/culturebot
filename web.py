import secrets
import traceback
from typing import Any, Optional, TYPE_CHECKING, Counter
from urllib.parse import quote, urlencode

import aiohttp
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel

if TYPE_CHECKING:
    from bot import CBot
    from cogs.memes import Memes

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

@app.get('/')
def index():
    return "Welcome to the index ig"

@app.get('/test/{status_code}')
def test(status_code: str):
    return Response(status_code=int(status_code))

@app.get('/oauth', name='discord oauth')
async def oauth(request: Request):
    """Handles oauth2 for discord"""
    state = secrets.token_urlsafe(32)
    
    url = "https://discord.com/oauth2/authorize?" + urlencode(
        {
            "response_type": "code",
            "client_id": app.bot.config.get('oauth', 'client_id'),
            "scope": "identify email",
            "state": state,
            "redirect_uri": request.url_for('oauth_callback')
        },
        quote_via=quote
    )
    response = RedirectResponse(url)
    response.set_cookie('oauth_state', state, max_age=600)
    return response
    
@app.get('/oauth/callback')
async def oauth_callback(code: str, state: str, request: Request):
    """Callback endpoint for discord oauth"""
    if request.cookies.get('oauth_state') != state:
        return JSONResponse({'error': 'state is incorrect'}, 403)
    
    data = {
        'client_id': app.bot.config.get('oauth', 'client_id'),
        'client_secret': app.bot.config.get('oauth', 'client_secret'),
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': request.url_for('oauth_callback')
    }
    
    async with aiohttp.ClientSession() as session:
        r = await session.post(
            "https://discord.com/api/v8/oauth2/token",
            data=data
        )
        data = await r.json()
    
    response = RedirectResponse(app.url_path_for('oauth_me'))
    response.set_cookie('oauth_access_token', data['access_token'], max_age=data['expires_in'])
    response.set_cookie('oauth_refresh_token', data['refresh_token'], httponly=True)
    return response

async def discord_request(endpoint: str, request: Request) -> Optional[Any]:
    """Sends a request to the discord api using oauth cookies in a request"""
    access_token = request.cookies.get('oauth_access_token')
    refresh_token = request.cookies.get('oauth_refresh_token')
    if access_token is None:
        return
    
    async with aiohttp.ClientSession() as session:
        r = await session.get(
            f"https://discord.com/api/v8/{endpoint}",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        if r.status == 200:
            return await r.json()
    

@app.get('/oauth/me')
async def oauth_me(request: Request):
    data = await discord_request('/users/@me', request)
    if data is None:
        return RedirectResponse('/oauth')
    
    # fuck templates, I'm too lazy
    avatar = f"https://cdn.discordapp.com/avatars/{data['id']}/{data['avatar']}.webp?size=256"
    return HTMLResponse(f"<img src={avatar}></img><br>"
                        f"Welcome <b>{data['username']}#{data['discriminator']}</b> ({data['email']})<br>"
                        f'<button type="button" onclick="location.href = \'/oauth/logout\';">Logout</button>')

@app.get('/oauth/logout')
async def oauth_logout():
    response = RedirectResponse('/')
    response.delete_cookie('oauth_access_token')
    response.delete_cookie('oauth_refresh_token')
    return response

@app.get('/genshin', deprecated=True)
def genshin():
    """Deprecated resource for getting genshin info of a user"""
    return RedirectResponse(
        "https://github.com/thesadru/genshinstats", 
        status_code=308
    )

@app.get('/stats', name='bot stats')
def stats():
    """Discord stats of the bot."""
    bot = app.bot
    return {
        'total_guilds': len(bot.guilds),
        'total_members': sum(guild.member_count for guild in bot.guilds),
        'uptime': bot.uptime.total_seconds()
    }

class SwearsGuildSwear(BaseModel):
    swear: str
    amount: int
class SwearsGuild(BaseModel):
    rank: int
    member: int
    swears: list[SwearsGuildSwear]
    total_swears: int
@app.get('/swears/{guild}', name='guild swears', response_model=list[SwearsGuild])
async def swears(guild: int):
    """A leaderboard of swears for a server"""
    # there is a proper way to do this but I can't be fucked.
    swears: list[tuple[int, dict[str, int]]] = [
        (doc['member'], doc['swears']) async for doc in 
        app.bot.db.culturebot.swears.find({'guild': guild})
    ]
    swears.sort(key=lambda x: sum(x[1].values()), reverse=True)
    return [
        {
            'rank': rank,
            'member': member,
            'swears': [{
                'swear': swear,
                'amount': amount
            } for swear, amount in swears.items()],
            'total_swears': sum(swears.values())
        }
        for rank, (member, swears) in enumerate(swears[:10], 1)
    ]

class SwearsMember(BaseModel):
    rank: int
    swear: str
    amount: int
@app.get('/swears/{guild}/{member}', name='member swears', response_model=list[SwearsMember])
async def swears_m(guild: int, member: int):
    """A leaderboard of swears for a server member"""
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
async def handle_internal_error(request: Request, exception: Exception):
    data = await discord_request('/users/@me', request)
    if data is not None and int(data['id']) == 454513969265115137:
        t = traceback.format_exception(type(exception), exception, exception.__traceback__)
        return HTMLResponse('<h1>500 Server Error Traceback</h1><pre>' + ''.join(t) + '</pre>', status_code=500)
    else:
        return HTMLResponse('<h1>500 Server Error</h1>', status_code=500)
