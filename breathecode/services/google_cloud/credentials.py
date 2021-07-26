"""
Google Cloud Credentials
"""
import os
import logging

logger = logging.getLogger(__name__)


def resolve_credentials():
    """Resolve Google Cloud credentials, returns True if is successfully"""
    path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', '')
    if not path:
        logger.error('GOOGLE_APPLICATION_CREDENTIALS is not set')
        return False

    if os.path.exists(path):
        return True

    credentials = os.getenv('GOOGLE_SERVICE_KEY', None)
    if not credentials:
        logger.error('GOOGLE_SERVICE_KEY is not set')
        return False

    with open(path, 'w') as credentials_file:
        credentials_file.write(credentials)
        return True
