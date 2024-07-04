"""
WSGI config for breathecode project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/howto/deployment/wsgi/
"""

# keeps this above
import newrelic.agent

newrelic.agent.initialize()

# the rest of your WSGI file contents go here
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "breathecode.settings")

application = get_wsgi_application()
application = newrelic.agent.WSGIApplicationWrapper(application)
