import asyncio
from typing import Counter
from aiohttp import web
from aiohttp.web_response import json_response

__all__ = ['app', 'run_app', 'stop_app']

app = web.Application()
routes = web.RouteTableDef()

@routes.get('/')
async def index(request: web.Request):
    """The index of the website"""
    return web.Response(text="Welcome to the culturebot api server.")

@routes.get('/api')
async def run(request: web.Request):
    """A list of all api paths"""
    return web.json_response({
        'message': "Welcome to the api, you can access database data through here.",
        'routes': [
            {
                'name': route.name or next(iter(route)).name or next(iter(route)).handler.__name__, 
                'path': route.canonical, 
                'routes': [
                    {
                        'name': res.name or res.handler.__name__, 
                        'method': res.method,
                        'description': res.handler.__doc__
                    } 
                    for res in route if res.method != 'HEAD']
            } 
            for route in app.router.resources() if route.canonical.startswith('/api')
        ]
    })

@routes.get('/api/genshin')
async def genshin(request: web.Request):
    """Deprecated resource for getting genshin info of a user"""
    raise web.HTTPPermanentRedirect(
        "https://github.com/thesadru/genshinstats", 
        reason="Due to the frequent abuse that caused everyone else to be ratelimited you are now encouraged to use the genshin api directly."
    )

@routes.get('/api/stats')
async def stats(request: web.Request):
    """Discord stats of the bot."""
    from bot import bot
    return json_response({
        'total_guilds': len(bot.guilds),
        'total_members': sum(guild.member_count for guild in bot.guilds),
        'uptime': bot.uptime.total_seconds()
    })

@routes.get('/api/swears')
async def swears(request: web.Request):
    """A leaderboard of swears for a server"""
    from bot import bot
    
    server = request.query.get('server') or request.query.get('guild')
    member = request.query.get('member') or request.query.get('user')
    if server is None:
        return json_response(
            {'message': 'You must provide a server paramater and an optional member parameter'}, 
            status=400
        )
    
    if member is None:
        # server stats
        c: Counter[int] = Counter()
        async for doc in bot.db.culturebot.swears.find({'guild': int(server)}):
            c[doc['member']] += sum(doc['swears'].values())
        return json_response([
            {
                'rank': rank,
                'member': member,
                'swears': amount
            }
            for rank, (member, amount) in enumerate(c.most_common(10), 1)
        ])
    else:
        # guild stats
        swears = await bot.db.culturebot.swears.find_one(
            {'member': int(member), 'guild': int(server)}
        )
        c = Counter(swears['swears'])
        return json_response([
            {
                'rank': rank,
                'swear': swear,
                'amount': amount
            }
            for rank, (swear, amount) in enumerate(c.most_common(10), 1)
        ])

app.add_routes(routes)

async def run_app(**kwargs):
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, **kwargs)
    await site.start()
    return runner, site
