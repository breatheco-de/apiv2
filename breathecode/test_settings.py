import os
from breathecode.settings import *

DATABASE_URL = os.getenv("DATABASE_URL", None)
# only use SQL Lite in localhost
if DATABASE_URL is None or "localhost" in DATABASE_URL:
    DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3'}}
