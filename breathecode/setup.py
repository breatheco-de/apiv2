import logging
import os
import ssl
from pathlib import Path

import redis

__all__ = ["resolve_gcloud_credentials", "configure_redis", "Lock"]

prev_path = None
prev_key = None


def is_test_env():
    return os.getenv("ENV") == "test"


IS_TEST_ENV = is_test_env()

logger = logging.getLogger(__name__)
redis_client = None
IS_HEROKU = os.getenv("DYNO", "") != ""


def configure_redis():
    ssl_ca_certs = os.getenv("REDIS_CA_CERT", None)
    ssl_certfile = os.getenv("REDIS_USER_CERT", None)
    ssl_keyfile = os.getenv("REDIS_USER_PRIVATE_KEY", None)
    if not (ssl_ca_certs and ssl_certfile and ssl_keyfile):
        return

    redis_ca_cert_path = Path(os.path.join(os.getcwd(), "redis_ca.pem"))
    redis_user_cert_path = Path(os.path.join(os.getcwd(), "redis_user.crt"))
    redis_user_private_key_path = Path(os.path.join(os.getcwd(), "redis_user_private.key"))

    with open(redis_ca_cert_path, "w") as f:
        f.write(ssl_ca_certs)

    with open(redis_user_cert_path, "w") as f:
        f.write(ssl_certfile)

    with open(redis_user_private_key_path, "w") as f:
        f.write(ssl_keyfile)

    return redis_ca_cert_path, redis_user_cert_path, redis_user_private_key_path


def get_redis_config():
    # production redis url
    redis_url = os.getenv("REDIS_COM_URL", "")
    redis_kwargs = {}
    settings = {}

    # local or heroku redis url

    if redis_url == "":
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

        # support for heroku redis addon
        if redis_url.startswith("redis://") and IS_HEROKU:
            redis_kwargs = {
                "broker_use_ssl": {
                    "ssl_cert_reqs": ssl.CERT_NONE,
                },
                "redis_backend_use_ssl": {
                    "ssl_cert_reqs": ssl.CERT_NONE,
                },
            }

    else:
        redis_ca_cert_path, redis_user_cert_path, redis_user_private_key_path = configure_redis()

        settings = {
            "ssl_cert_reqs": ssl.CERT_REQUIRED,
            "ssl_ca_certs": redis_ca_cert_path,
            "ssl_certfile": redis_user_cert_path,
            "ssl_keyfile": redis_user_private_key_path,
        }

        redis_kwargs = {
            "broker_use_ssl": settings,
            "redis_backend_use_ssl": settings,
        }

    # overwrite the redis url with the new one
    os.environ["REDIS_URL"] = redis_url
    return settings, redis_kwargs, redis_url


def get_redis():
    global redis_client

    settings, _, redis_url = get_redis_config()

    if redis_client == None:
        redis_client = redis.from_url(redis_url, **settings)

    return redis_client


if not IS_TEST_ENV:
    from redis.lock import Lock
else:

    class Lock:

        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            pass

        def __exit__(self, *args, **kwargs):
            pass


def resolve_gcloud_credentials():
    """Resolve Google Cloud credentials, returns True if it's successfully."""

    global prev_path, prev_key

    # avoid manage credentials if they are already set
    if is_test_env() is False and (
        prev_path
        and prev_path == os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        and (
            (prev_key and prev_key == os.getenv("GOOGLE_SERVICE_KEY"))
            or (prev_key == None and os.getenv("GOOGLE_SERVICE_KEY") == None)
        )
    ):
        logger.info("GOOGLE_APPLICATION_CREDENTIALS and GOOGLE_SERVICE_KEY are already set")
        return True

    path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not path:
        logger.error("GOOGLE_APPLICATION_CREDENTIALS is not set")
        return False

    path = Path(os.path.join(os.getcwd(), path))
    prev_path = str(path)

    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = prev_path

    if os.path.exists(path):
        return True

    credentials = os.getenv("GOOGLE_SERVICE_KEY")
    if not credentials:
        logger.error("GOOGLE_SERVICE_KEY is not set")
        return False

    prev_key = credentials

    with open(path, "w") as credentials_file:
        credentials_file.write(credentials)
        return True
