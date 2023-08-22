"""
Google Cloud Credentials
"""
import os
import logging

from pathlib import Path

logger = logging.getLogger(__name__)

__all__ = ['resolve_credentials']

prev_path = None
prev_key = None


def resolve_credentials():
    """Resolve Google Cloud credentials, returns True if it's successfully."""

    global prev_path, prev_key

    # avoid manage credentials if they are already set
    if (prev_path and prev_path == os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
            and ((prev_key and prev_key == os.getenv('GOOGLE_SERVICE_KEY')) or
                 (prev_key == None and os.getenv('GOOGLE_SERVICE_KEY') == None))):
        logger.info('GOOGLE_APPLICATION_CREDENTIALS and GOOGLE_SERVICE_KEY are already set')
        return True

    path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    if not path:
        logger.error('GOOGLE_APPLICATION_CREDENTIALS is not set')
        return False

    path = Path(os.path.join(os.getcwd(), path))
    prev_path = str(path)

    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = prev_path

    if os.path.exists(path):
        return True

    credentials = os.getenv('GOOGLE_SERVICE_KEY')
    if not credentials:
        logger.error('GOOGLE_SERVICE_KEY is not set')
        return False

    prev_key = credentials

    with open(path, 'w') as credentials_file:
        credentials_file.write(credentials)
        return True
