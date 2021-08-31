import asyncio
import secrets
from typing import Any, Dict, Optional
from urllib.parse import quote as urlquote
from urllib.parse import urlencode

import aiohttp
from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from starlette.responses import Response
from utils import config

app = FastAPI(docs_url=None, redoc_url=None)


class NoAccessToken(Exception):
    def __init__(self, message=None) -> None:
        super().__init__(message or "No oauth access token found, please authorize")


class DiscordClient:
    def __init__(self, access_token: str, refresh_token: str = None) -> None:
        self.access_token = access_token
        self.refresh_token = refresh_token

    @property
    def session(self):
        if not hasattr(self, "_session"):
            self._session = aiohttp.ClientSession()

        return self._session

    def __del__(self):
        try:
            asyncio.create_task(self._session.close())
        except:
            pass

    @classmethod
    async def from_code(cls, code: str, redirect_uri: str):
        session = aiohttp.ClientSession()
        r = await session.post(
            "https://discord.com/api/v8/oauth2/token",
            data={
                "client_id": config.get("oauth", "client_id"),
                "client_secret": config.get("oauth", "client_secret"),
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
            },
        )
        data = await r.json()
        print(data)
        self = cls(data["access_token"], data["refresh_token"])
        self._session = session
        return self

    async def request(self, endpoint: str, **kwargs: Any) -> Any:
        for _ in range(3):
            r = await self.session.get(
                f"https://discord.com/api/v8/{endpoint}", headers={"Authorization": f"Bearer {self.access_token}"}, **kwargs
            )
            if r.status == 200:
                return await r.json()
            else:
                await self.refresh_access_token()

    async def refresh_access_token(self) -> None:
        r = await self.session.post(
            "https://discord.com/api/v8/oauth2/token",
            data={
                "client_id": config.get("oauth", "client_id"),
                "client_secret": config.get("oauth", "client_secret"),
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
            },
        )
        data = await r.json()
        self.access_token = data['access_token']
        self.refresh_token = data['refresh_token']

    async def me(self) -> dict[str, Any]:
        return await self.request("/users/@me")

    def add_cookies(self, response: Response) -> None:
        response.set_cookie("oauth_access_token", self.access_token, max_age=None)
        response.set_cookie("oauth_refresh_token", self.refresh_token or "", httponly=True)


async def discord_client(request: Request) -> DiscordClient:
    access = request.cookies.get("oauth_access_token")
    refresh = request.cookies.get("oauth_refresh_token")

    if access is None:
        raise NoAccessToken()

    return DiscordClient(access, refresh)


@app.get("/")
async def oauth(request: Request):
    """Handles oauth2 for discord"""
    state = secrets.token_urlsafe(16)

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

    client = await DiscordClient.from_code(code, request.url_for("oauth_callback"))

    response = RedirectResponse(request.url_for("oauth_me"))
    response.set_cookie("oauth_access_token", client.access_token, max_age=None)
    response.set_cookie("oauth_refresh_token", client.refresh_token or "", httponly=True)
    return response


@app.get("/me")
async def oauth_me(request: Request, client: DiscordClient = Depends(discord_client)):
    data = await client.me()

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
