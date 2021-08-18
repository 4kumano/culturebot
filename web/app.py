import traceback

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from .oauth import discord_request

app = FastAPI(docs_url=None, redoc_url=None)

@app.get("/")
def index():
    return "Welcome to the index ig"

@app.exception_handler(Exception)
async def handle_internal_error(request: Request, exception: Exception):
    data = await discord_request("/users/@me", request)
    if data is not None and int(data["id"]) == 454513969265115137:
        t = traceback.format_exception(type(exception), exception, exception.__traceback__)
        return HTMLResponse("<h1>500 Server Error Traceback</h1><pre>" + "".join(t) + "</pre>", status_code=500)
    else:
        return HTMLResponse("<h1>500 Server Error</h1>", status_code=500)
