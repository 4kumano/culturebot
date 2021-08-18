__all__ = ["app"]

from .app import app
from . import api, oauth

app.mount("/api", api.app)
app.mount("/oauth", oauth.app)
