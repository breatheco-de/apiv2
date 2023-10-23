import logging
import os
from pathlib import Path

__all__ = ['configure_redis']

logger = logging.getLogger(__name__)


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
