"""
ASGI config for mysite project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/asgi/
"""

import os

if os.getenv('UVLOOP') == '1':
    import asyncio

    import uvloop

    # Set the event loop policy to uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')

application = get_asgi_application()
