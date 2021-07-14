import asyncio
from aiohttp import web

__all__ = ['app', 'run_app']

app = web.Application()
routes = web.RouteTableDef()

@routes.get('/')
async def index(request: web.Request):
    return web.Response(text="Welcome to the culturebot api server. You can run commands through here using /run")

@routes.get('/run')
async def run(request: web.Request):
    return web.Response(text="Not implemented yet", status=500)

app.add_routes(routes)

def run_app(**kwargs):
    asyncio.create_task(web._run_app(app, print=None, **kwargs))