"""
WSGI config for breathecode project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/howto/deployment/wsgi/
"""

# keeps this above
import newrelic.agent

newrelic.agent.initialize()

# the rest of your ASGI file contents go here
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'breathecode.settings')

application = get_asgi_application()
# disable until I can make it work
# application = newrelic.agent.ASGIApplicationWrapper(application=application)
