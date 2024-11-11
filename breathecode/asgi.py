"""
WSGI config for breathecode project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/howto/deployment/wsgi/
"""

import os

from channels.routing import ProtocolTypeRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "breathecode.settings")

http_application = get_asgi_application()

from .websocket.router import routes

application = ProtocolTypeRouter(
    {
        "http": http_application,
        "websocket": routes,
        # Just HTTP for now. (We can add other protocols later.)
    }
)
