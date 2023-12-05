# that file is save outside of breathecode for evit load celery with development environment
import os

os.environ['ENV'] = 'test'

from breathecode.settings import *  # noqa: F401

from django.core.cache.backends.locmem import LocMemCache
import fnmatch

DEBUG = True

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///:memory:')
os.environ['DATABASE_URL'] = DATABASE_URL

# only use SQL Lite in localhost
# if DATABASE_URL is None or 'localhost' in DATABASE_URL:
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}

CACHES = {
    'default': {
        'BACKEND': 'breathecode.settings.CustomMemCache',
        'LOCATION': 'breathecode',
    },
}

CACHE_MIDDLEWARE_SECONDS = 60 * int(os.getenv('CACHE_MIDDLEWARE_MINUTES', 120))


class Key(TypedDict):
    key: str
    value: str
    valid_until: datetime


# TODO: support timeout
class CustomMemCache(LocMemCache):
    _cache = {}

    def delete_many(self, patterns):
        for pattern in patterns:
            self.delete(pattern)

    def delete(self, key, *args, **kwargs):
        if key in self._cache.keys():
            del self._cache[key]

    def keys(self, filter=None):
        if filter:
            return sorted(fnmatch.filter(self._cache.keys(), filter))

        return sorted(self._cache.keys())

    def clear(self):
        self._cache = {}

    # TODO: timeout not implemented yet
    def set(self, key, value, *args, timeout=None, **kwargs):
        if value is None:
            self._cache[key] = None
            return

        self._cache[key] = {
            'key': key,
            'value': value,
            'valid_until': timeout,
        }

    def get(self, key, *args, **kwargs):
        if key not in self._cache.keys():
            return None

        return self._cache[key]['value']


CACHES['default'] = {
    **CACHES['default'],
    'LOCATION': 'breathecode',
    'BACKEND': 'breathecode.settings.CustomMemCache',
}
