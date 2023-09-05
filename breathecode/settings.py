"""
Django settings for breathecode project.

Generated by 'django-admin startproject' using Django 3.0.7.
For more information on this file, see
https://docs.djangoproject.com/en/3.0/topics/settings/
For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.0/ref/settings/
"""

import os
from pathlib import Path
import django_heroku
import dj_database_url
import json
import logging
from django.contrib.messages import constants as messages
from django.utils.log import DEFAULT_LOGGING

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

DATABASE_URL = os.environ.get('DATABASE_URL')
ENVIRONMENT = os.environ.get('ENV')

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '5ar3h@ha%y*dc72z=8-ju7@4xqm0o59*@k*c2i=xacmy2r=%4a'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = (ENVIRONMENT == 'development' or ENVIRONMENT == 'test')

ALLOWED_HOSTS = []

# Application definition

INSTALLED_APPS = [
    'whitenoise.runserver_nostatic',
    'breathecode.admin_styles',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django.contrib.postgres',
    'django.contrib.admindocs',
    'rest_framework',
    'phonenumber_field',
    'corsheaders',
    'breathecode.notify',
    'breathecode.authenticate',
    'breathecode.monitoring',
    'breathecode.admissions',
    'breathecode.events',
    'breathecode.feedback',
    'breathecode.assignments',
    'breathecode.marketing',
    'breathecode.freelance',
    'breathecode.certificate',
    'breathecode.media',
    'breathecode.assessment',
    'breathecode.registry',
    'breathecode.mentorship',
    'breathecode.career',
    'breathecode.commons',
    'breathecode.websocket',
    'breathecode.payments',
    'breathecode.provisioning',
    'explorer',
    'channels',
]

if os.getenv('ALLOW_UNSAFE_CYPRESS_APP') or ENVIRONMENT == 'test':
    INSTALLED_APPS.append('breathecode.cypress')

REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS':
    'rest_framework.schemas.openapi.AutoSchema',
    'DEFAULT_VERSIONING_CLASS':
    'rest_framework.versioning.NamespaceVersioning',
    'DEFAULT_PAGINATION_CLASS':
    'breathecode.utils.HeaderLimitOffsetPagination',
    'EXCEPTION_HANDLER':
    'breathecode.utils.breathecode_exception_handler',
    'PAGE_SIZE':
    100,
    'DEFAULT_VERSION':
    'v1',
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'breathecode.authenticate.authentication.ExpiringTokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
        'rest_framework_csv.renderers.CSVRenderer',
    ),
}

MIDDLEWARE = []

if ENVIRONMENT == 'development':

    def just_admin(request):
        return request.user.is_staff

    MIDDLEWARE += [
        'silk.middleware.SilkyMiddleware',
    ]

    INSTALLED_APPS += [
        'silk',
    ]

    SILKY_PYTHON_PROFILER = True
    SILKY_PYTHON_PROFILER_BINARY = True
    SILKY_PYTHON_PROFILER_RESULT_PATH = '/tmp'

    SILKY_AUTHENTICATION = True
    SILKY_AUTHORISATION = False
    SILKY_AUTHORISATION_FUNCTION = just_admin

    SILKY_META = True
    SILKY_ANALYZE_QUERIES = True

if ENVIRONMENT != 'production':
    import resource

    class MemoryUsageMiddleware:

        def __init__(self, get_response):
            self.get_response = get_response

        def __call__(self, request):
            start_mem = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            response = self.get_response(request)
            end_mem = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            delta_mem = end_mem - start_mem
            print(f'Memory usage for this request: {delta_mem} KB')
            response['X-Memory-Usage'] = f'{delta_mem} KB'
            return response

    MIDDLEWARE += [
        'breathecode.settings.MemoryUsageMiddleware',
    ]

MIDDLEWARE += [
    # 'rollbar.contrib.django.middleware.RollbarNotifierMiddlewareOnly404',
    # ⬆ This Rollbar should always be first please!
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',

    # Cache
    # 'django.middleware.cache.UpdateCacheMiddleware',
    'django.middleware.common.CommonMiddleware',
    # 'django.middleware.cache.FetchFromCacheMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    #'breathecode.utils.admin_timezone.TimezoneMiddleware',

    # ⬇ Rollbar is always last please!
    # 'rollbar.contrib.django.middleware.RollbarNotifierMiddlewareExcluding404',
]

AUTHENTICATION_BACKENDS = ('django.contrib.auth.backends.ModelBackend', )

ROOT_URLCONF = 'breathecode.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.request',
            ],
        },
    },
]

WSGI_APPLICATION = 'breathecode.wsgi.application'

# Password validation
# https://docs.djangoproject.com/en/3.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Disable Django's logging setup
LOGGING_CONFIG = None

IS_TEST_ENV = os.getenv('ENV') == 'test'
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()

# this prevent the duplications of logs because heroku redirect the output to Coralogix
if IS_TEST_ENV:
    LOGGING_HANDLERS = ['console']

else:
    LOGGING_HANDLERS = ['coralogix', 'console']

logging.config.dictConfig({
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            # exact format is not important, this is the minimum information
            'format': '[%(asctime)s] %(name)-12s %(levelname)-8s %(message)s',
        },
        'django.server': DEFAULT_LOGGING['formatters']['django.server'],
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'handlers': {
        'coralogix': {
            'class': 'coralogix.handlers.CoralogixLogger',
            'formatter': 'default',
            'private_key': os.getenv('CORALOGIX_PRIVATE_KEY', ''),
            'app_name': os.getenv('CORALOGIX_APP_NAME', 'localhost'),
            'subsystem': os.getenv('CORALOGIX_SUBSYSTEM', 'logger'),
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'default',
        },
        'django.server': DEFAULT_LOGGING['handlers']['django.server'],
    },
    'loggers': {
        '': {
            'level': 'WARNING',
            'handlers': LOGGING_HANDLERS,
        },
        # Our application code
        'breathecode': {
            'level': LOG_LEVEL,
            'handlers': LOGGING_HANDLERS,
            # Avoid double logging because of root logger
            'propagate': False,
        },
        # Prevent noisy modules from logging to Sentry
        'noisy_module': {
            'level': 'ERROR',
            'handlers': LOGGING_HANDLERS,
            'propagate': False,
        },
        # Default runserver request logging
        'django.server': DEFAULT_LOGGING['loggers']['django.server'],
    }
})

ROLLBAR = {
    'access_token': os.getenv('ROLLBAR_ACCESS_TOKEN', ''),
    'environment': 'development' if DEBUG else 'production',
    'branch': 'master',
    'root': BASE_DIR,
    # parsed POST variables placed in your output for exception handling
    'EXCEPTION_HANDLER': 'rollbar.contrib.django_rest_framework.post_exception_handler',
}

MESSAGE_TAGS = {
    messages.DEBUG: 'alert-info',
    messages.INFO: 'alert-info',
    messages.SUCCESS: 'alert-success',
    messages.WARNING: 'alert-warning',
    messages.ERROR: 'alert-danger',
}

# Internationalization
# https://docs.djangoproject.com/en/3.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Honor the 'X-Forwarded-Proto' header for request.is_secure()
# SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Allow all host headers
ALLOWED_HOSTS = ['*']

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.0/howto/static-files/

# static generated automatically
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATIC_URL = '/static/'

STATICFILES_DIRS = [
    # static generated by us
    os.path.join(PROJECT_ROOT, 'static'),
]

CORS_ORIGIN_ALLOW_ALL = True

CORS_ALLOW_HEADERS = [
    'accept',
    'academy',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'cache-control',
    'credentials',
    'http-access-control-request-method',
]

REDIS_URL = os.getenv('REDIS_URL', '')

IS_REDIS_WITH_SSL = REDIS_URL.startswith('rediss://')

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'ssl_cert_reqs': None
            },
        }
    }
}

if IS_TEST_ENV:
    del CACHES['default']['OPTIONS']
    CACHES['default'] = {
        **CACHES['default'],
        'LOCATION': 'breathecode',
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }

elif not IS_REDIS_WITH_SSL:
    del CACHES['default']['OPTIONS']

CACHE_MIDDLEWARE_SECONDS = 60 * int(os.getenv('CACHE_MIDDLEWARE_MINUTES', 120))

# Simplified static file serving.
# https://warehouse.python.org/project/whitenoise/
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

SITE_ID = 1

# Change 'default' database configuration with $DATABASE_URL.
# https://github.com/jacobian/dj-database-url#url-schema
DATABASES = {
    'default': dj_database_url.config(default=DATABASE_URL, ssl_require=False),
}
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

# SQL Explorer
EXPLORER_CONNECTIONS = {'Default': 'default'}
EXPLORER_DEFAULT_CONNECTION = 'default'

sql_keywords_path = Path(os.getcwd()) / 'breathecode' / 'sql_keywords.json'
with open(sql_keywords_path, 'r') as f:
    sql_keywords = json.load(f)

    # https://www.postgresql.org/docs/8.1/sql-keywords-appendix.html
    # scripts/update_sql_keywords_json.py
    # breathecode/sql_keywords.json

    EXPLORER_SQL_BLACKLIST = tuple(sql_keywords['blacklist'])

# Django Rest Hooks
HOOK_EVENTS = {
    # 'any.event.name': 'App.Model.Action' (created/updated/deleted)
    'form_entry.added': 'marketing.FormEntry.created+',
    'form_entry.changed': 'marketing.FormEntry.updated+',
    'profile_academy.added': 'authenticate.ProfileAcademy.created+',
    'profile_academy.changed': 'authenticate.ProfileAcademy.updated+',
    'cohort_user.added': 'admissions.CohortUser.created+',
    'cohort_user.changed': 'admissions.CohortUser.updated+',

    # and custom events, make sure to trigger them at notify.receivers.py
    'cohort_user.edu_status_updated': 'admissions.CohortUser.edu_status_updated',
    'user_invite.invite_status_updated': 'authenticate.UserInvite.invite_status_updated',
    'asset.asset_status_updated': 'registry.Asset.asset_status_updated',
    'event.event_status_updated': 'events.Event.event_status_updated',
    'event.new_event_order': 'events.EventCheckin.new_event_order',
    'event.new_event_attendee': 'events.EventCheckin.new_event_attendee',
    'form_entry.won_or_lost': 'marketing.FormEntry.won_or_lost',
    'session.mentorship_session_status': 'mentorship.MentorshipSession.mentorship_session_status',
}

# Websocket
ASGI_APPLICATION = 'breathecode.asgi.application'
REDIS_URL_PATTERN = r'^redis://(.+):(\d+)$'

heroku_redis_ssl_host = {
    'address': REDIS_URL,  # The 'rediss' schema denotes a SSL connection.
}

if IS_REDIS_WITH_SSL:
    heroku_redis_ssl_host['address'] += '?ssl_cert_reqs=none'

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': (heroku_redis_ssl_host, ),
        },
    },
}

if IS_TEST_ENV:
    del CHANNEL_LAYERS['default']['CONFIG']
    CHANNEL_LAYERS['default'] = {
        **CHANNEL_LAYERS['default'],
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    }

# keep last part of the file
django_heroku.settings(locals(), databases=False)
