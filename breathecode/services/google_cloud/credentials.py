"""Google Cloud Credentials."""

import logging

from breathecode.setup import resolve_gcloud_credentials

logger = logging.getLogger(__name__)

__all__ = ["resolve_credentials"]


def resolve_credentials():
    """Resolve Google Cloud credentials, returns True if it's successfully."""

    return resolve_gcloud_credentials()
