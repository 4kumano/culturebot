from __future__ import annotations

import asyncio
import secrets
from typing import Any, ClassVar, Optional
from urllib.parse import quote as urlquote
from urllib.parse import urlencode

import aiohttp
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from starlette.responses import Response
from utils import config

app = FastAPI(docs_url=None, redoc_url=None)


class Unauthorized(Exception):
    pass


class RefreshedToken(Exception):
    def __init__(self, client: DiscordClient) -> None:
        self.client = client
        super().__init__()


class DiscordClient:
    client_id: ClassVar[str] = config.get("oauth", "client_id")
    client_secret: ClassVar[str] = config.get("oauth", "client_secret")

    access_token: Optional[str]
    refresh_token: Optional[str]
    allow_refresh: bool

    def __init__(self, access_token: str = None, refresh_token: str = None, allow_refresh: bool = True) -> None:
        if not access_token and not refresh_token:
            raise TypeError("Either an access token or a refresh token is required")

        self.access_token = access_token
        self.refresh_token = refresh_token
        self.allow_refresh = allow_refresh
        self._me = None

    def __del__(self):
        try:
            asyncio.create_task(self._session.close())
        except:
            pass

    @property
    def session(self):
        if not hasattr(self, "_session"):
            self._session = aiohttp.ClientSession()

        return self._session

    @classmethod
    async def from_code(cls, code: str, redirect_uri: str):
        session = aiohttp.ClientSession()
        r = await session.post(
            "https://discord.com/api/v8/oauth2/token",
            data={
                "client_id": cls.client_id,
                "client_secret": cls.client_secret,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
            },
        )
        data = await r.json()

        self = cls(data["access_token"], data["refresh_token"])
        self._session = session
        return self

    @classmethod
    def from_request(cls, request: Request, **kwargs) -> Optional[DiscordClient]:
        auth_header: str = request.headers.get("authorization")

        if auth_header:
            scheme, _, access_token = auth_header.partition(" ")
            if scheme.lower() != "bearer":
                raise HTTPException(403, "Authorization scheme is incorrect")
            refresh_token = None
        else:
            access_token = request.cookies.get("oauth_access_token")
            refresh_token = request.cookies.get("oauth_refresh_token")

            if access_token is None and refresh_token is None:
                return None

        return cls(access_token, refresh_token, **kwargs)

    async def request(self, endpoint: str, **kwargs: Any) -> Any:
        r = await self.session.get(
            f"https://discord.com/api/v8/{endpoint}", headers={"Authorization": f"Bearer {self.access_token}"}, **kwargs
        )
        data = await r.json()
        if r.status == 200:
            return data
        elif self.allow_refresh and self.refresh_token:
            await self.refresh_access_token()
            return await self.request(endpoint, **kwargs)
        
        raise Exception(data['message'])

    async def refresh_access_token(self) -> None:
        r = await self.session.post(
            "https://discord.com/api/v8/oauth2/token",
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
            },
        )
        data = await r.json()
        if "error" in data:
            raise Unauthorized

        self.access_token = data["access_token"]
        self.refresh_token = data["refresh_token"]

    async def me(self) -> dict[str, Any]:
        if self._me is None:
            self._me = await self.request("/users/@me")
        return self._me

    def add_cookies(self, response: Response) -> None:
        if self.access_token:
            response.set_cookie("oauth_access_token", self.access_token, max_age=None)
        if self.refresh_token:
            response.set_cookie("oauth_refresh_token", self.refresh_token, httponly=True)


async def discord_client(request: Request, response: Response) -> DiscordClient:
    client = DiscordClient.from_request(request)
    if client is None:
        raise Unauthorized

    access, refresh = client.access_token, client.refresh_token
    await client.me()
    if access != client.access_token or refresh != client.refresh_token:
        raise RefreshedToken(client)

    return client


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
async def oauth_callback(request: Request, code: str, state: str):
    """Callback endpoint for discord oauth"""
    if request.cookies.get("oauth_state") != state:
        return JSONResponse({"error": "state is incorrect"}, 403)

    client = await DiscordClient.from_code(code, request.url_for("oauth_callback"))

    response = RedirectResponse(request.url_for("oauth_me"))
    client.add_cookies(response)
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


@app.exception_handler(RefreshedToken)
async def handle_refreshed_token(request: Request, exception: RefreshedToken):
    client = exception.client
    response = RedirectResponse(request.url)
    client.add_cookies(response)
    return response


@app.exception_handler(Unauthorized)
async def handle_unauthorized(request: Request, exception: Unauthorized):
    return RedirectResponse(request.url_for("oauth"))
