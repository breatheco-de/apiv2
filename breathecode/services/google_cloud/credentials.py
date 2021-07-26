"""
Google Cloud Credentials
"""
import os
import logging

from pathlib import Path

logger = logging.getLogger(__name__)


def resolve_credentials():
    """Resolve Google Cloud credentials, returns True if is successfully"""
    path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', '')
    if not path:
        logger.error('GOOGLE_APPLICATION_CREDENTIALS is not set')
        return False

    path = Path(os.path.join(os.getcwd(), path))
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(path)

    if os.path.exists(path):
        return True

    credentials = os.getenv('GOOGLE_SERVICE_KEY', None)
    if not credentials:
        logger.error('GOOGLE_SERVICE_KEY is not set')
        return False

    with open(path, 'w') as credentials_file:
        credentials_file.write(credentials)
        return True
