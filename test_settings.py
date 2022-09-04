# that file is save outside of breathecode for evit load celery with development environment
import os

os.environ['ENV'] = 'test'

from breathecode.settings import *

DATABASE_URL = os.getenv('DATABASE_URL', None)
# only use SQL Lite in localhost
# if DATABASE_URL is None or 'localhost' in DATABASE_URL:
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'breathecode',
    },
}

CACHE_MIDDLEWARE_SECONDS = 60 * int(os.getenv('CACHE_MIDDLEWARE_MINUTES', 120))
