"""
Google Cloud Credentials
"""
import os
from ...decorators import run_once


@run_once
def resolve_credentials():
    """Resolve Google Cloud Credentials"""
    path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', '')

    if os.path.exists(path):
        return True

    credentials = os.getenv('GOOGLE_SERVICE_KEY', None)
    # skip open in development environment
    if credentials and os.getenv('ENV') != 'development':
        with open(path, 'w') as credentials_file:
            credentials_file.write(credentials)
