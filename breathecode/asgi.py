"""
ASGI config for breathecode project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'breathecode.settings')

django.setup()
app = get_asgi_application()

from django.conf import settings
import breathecode.settings as app_settings

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from breathecode.websocket.urls import websocket_urlpatterns

settings.configure(INSTALLED_APPS=app_settings.INSTALLED_APPS, DATABASES=app_settings.DATABASES)

application = ProtocolTypeRouter({
    'http': app,
    'websocket': AuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
})
