import logging
import os
import redis
import ssl
from pathlib import Path

__all__ = ['configure_redis']

logger = logging.getLogger(__name__)
redis_client = None
IS_HEROKU = os.getenv('DYNO', '') != ''


def configure_redis():
    ssl_ca_certs = os.getenv('REDIS_CA_CERT', None)
    ssl_certfile = os.getenv('REDIS_USER_CERT', None)
    ssl_keyfile = os.getenv('REDIS_USER_PRIVATE_KEY', None)
    if not (ssl_ca_certs and ssl_certfile and ssl_keyfile):
        return

    redis_ca_cert_path = Path(os.path.join(os.getcwd(), 'redis_ca.pem'))
    redis_user_cert_path = Path(os.path.join(os.getcwd(), 'redis_user.crt'))
    redis_user_private_key_path = Path(os.path.join(os.getcwd(), 'redis_user_private.key'))

    with open(redis_ca_cert_path, 'w') as f:
        f.write(ssl_ca_certs)

    with open(redis_user_cert_path, 'w') as f:
        f.write(ssl_certfile)

    with open(redis_user_private_key_path, 'w') as f:
        f.write(ssl_keyfile)

    return redis_ca_cert_path, redis_user_cert_path, redis_user_private_key_path


def get_redis_config():
    # production redis url
    REDIS_URL = os.getenv('REDIS_COM_URL', '')
    redis_kwargs = {}
    settings = {}

    # local or heroku redis url

    if REDIS_URL == '':
        REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')

        # support for heroku redis addon
        if REDIS_URL.startswith('redis://') and IS_HEROKU:
            redis_kwargs = {
                'broker_use_ssl': {
                    'ssl_cert_reqs': ssl.CERT_NONE,
                },
                'redis_backend_use_ssl': {
                    'ssl_cert_reqs': ssl.CERT_NONE,
                }
            }

    else:
        redis_ca_cert_path, redis_user_cert_path, redis_user_private_key_path = configure_redis()

        settings = {
            'ssl_cert_reqs': ssl.CERT_REQUIRED,
            'ssl_ca_certs': redis_ca_cert_path,
            'ssl_certfile': redis_user_cert_path,
            'ssl_keyfile': redis_user_private_key_path,
        }

        redis_kwargs = {
            'broker_use_ssl': settings,
            'redis_backend_use_ssl': settings,
        }

    # overwrite the redis url with the new one
    os.environ['REDIS_URL'] = REDIS_URL
    return settings, redis_kwargs, REDIS_URL


def get_redis():
    global redis_client

    settings, redis_kwargs, REDIS_URL = get_redis_config()

    if redis_client == None:
        redis_client = redis.from_url(REDIS_URL, **settings)

    return redis_client
