import asyncio
from aiohttp import web

__all__ = ['app', 'run_app']

app = web.Application()
routes = web.RouteTableDef()

@routes.get('/')
async def keep_alive(request: web.Request):
    return web.Response(text="Hello World!")

app.add_routes(routes)

def run_app(**kwargs):
    asyncio.create_task(web._run_app(app, print=None, **kwargs))