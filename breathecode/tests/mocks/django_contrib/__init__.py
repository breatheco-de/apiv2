"""
Django contrib Mocks
"""

from unittest.mock import Mock
from .messages_mock import MessagesMock

DJANGO_CONTRIB_PATH = {
    "messages": "django.contrib.messages",
}

DJANGO_CONTRIB_INSTANCES = {
    "messages": Mock(side_effect=MessagesMock),
}


def apply_django_contrib_messages_mock():
    """Apply Storage Messages Mock"""
    return DJANGO_CONTRIB_INSTANCES["messages"]
