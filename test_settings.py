# that file is save outside of breathecode for evit load celery with development environment
import os

os.environ["ENV"] = "test"

from breathecode.settings import *  # noqa: F401

DEBUG = True

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///:memory:")
os.environ["DATABASE_URL"] = DATABASE_URL

# only use SQL Lite in localhost
# if DATABASE_URL is None or 'localhost' in DATABASE_URL:
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}

CACHES = {
    "default": {
        "BACKEND": "breathecode.settings.CustomMemCache",
        "LOCATION": "breathecode",
    },
}

CACHE_MIDDLEWARE_SECONDS = 60 * int(os.getenv("CACHE_MIDDLEWARE_MINUTES", 120))
SECURE_SSL_REDIRECT = False
