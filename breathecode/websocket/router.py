from channels.auth import AuthMiddlewareStack
from channels.routing import URLRouter
from channels.security.websocket import AllowedHostsOriginValidator

from django.urls import path

from .consumers import NotificationConsumer

routes = AllowedHostsOriginValidator(
    AuthMiddlewareStack(
        URLRouter(
            [
                path("ws/notification", NotificationConsumer.as_asgi(), name="ws_notification"),
            ]
        )
    )
)
