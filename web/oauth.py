import secrets
from typing import Any, Optional
from urllib.parse import quote as urlquote
from urllib.parse import urlencode

import aiohttp
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from utils import config

app = FastAPI(docs_url=None, redoc_url=None)

async def discord_request(endpoint: str, request: Request) -> Optional[Any]:
    """Sends a request to the discord api using oauth cookies in a request"""
    access_token = request.cookies.get("oauth_access_token")
    refresh_token = request.cookies.get("oauth_refresh_token")
    
    async with aiohttp.ClientSession() as session:        
        r = await session.get(
            f"https://discord.com/api/v8/{endpoint}", headers={"Authorization": f"Bearer {access_token}"}
        )
        if r.status == 200:
            return await r.json()

@app.get("/", name="discord oauth")
async def oauth(request: Request):
    """Handles oauth2 for discord"""
    state = secrets.token_urlsafe(32)

    url = "https://discord.com/oauth2/authorize?" + urlencode(
        {
            "response_type": "code",
            "client_id": config.get("oauth", "client_id"),
            "scope": "identify email",
            "state": state,
            "redirect_uri": request.url_for("oauth_callback"),
        },
        quote_via=urlquote,
    )
    response = RedirectResponse(url)
    response.set_cookie("oauth_state", state, max_age=600)
    return response

@app.get("/callback")
async def oauth_callback(code: str, state: str, request: Request):
    """Callback endpoint for discord oauth"""
    if request.cookies.get("oauth_state") != state:
        return JSONResponse({"error": "state is incorrect"}, 403)

    async with aiohttp.ClientSession() as session:
        r = await session.post(
            "https://discord.com/api/v8/oauth2/token",
            data={
                "client_id": config.get("oauth", "client_id"),
                "client_secret": config.get("oauth", "client_secret"),
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": request.url_for("oauth_callback"),
            },
        )
        data = await r.json()

    response = RedirectResponse(request.url_for("oauth_me"))
    response.set_cookie("oauth_access_token", data["access_token"], max_age=data["expires_in"])
    response.set_cookie("oauth_refresh_token", data["refresh_token"], httponly=True)
    return response

@app.get("/me")
async def oauth_me(request: Request):
    data = await discord_request("/users/@me", request)
    if data is None:
        return RedirectResponse("/oauth")

    # fuck templates, I'm too lazy
    avatar = f"https://cdn.discordapp.com/avatars/{data['id']}/{data['avatar']}.webp?size=256"
    return HTMLResponse(
        f"<img src={avatar}></img><br>"
        f"Welcome <b>{data['username']}#{data['discriminator']}</b> ({data['email']})<br>"
        f'<a href="{request.url_for("oauth_logout")}"><button>Logout</button></a>'
    )

@app.get("/logout")
async def oauth_logout():
    response = RedirectResponse("/")
    response.delete_cookie("oauth_access_token")
    response.delete_cookie("oauth_refresh_token")
    return response
