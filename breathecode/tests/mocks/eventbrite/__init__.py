"""
Google Cloud Storage Mocks
"""
from unittest.mock import Mock
from .requests_mock import request_mock
from .constants import (EVENTBRITE_EVENT, EVENTBRITE_ORDER,
                        EVENTBRITE_ATTENDEE, EVENTBRITE_TICKET_CLASS,
                        EVENTBRITE_EVENT_URL, EVENTBRITE_ORDER_URL,
                        EVENTBRITE_ATTENDEE_URL, EVENTBRITE_TICKET_CLASS_URL)

EVENTBRITE_PATH = {
    'get': 'requests.get',
}

EVENTBRITE_INSTANCES = {'get': Mock(side_effect=request_mock)}


def apply_eventbrite_requests_post_mock():
    """Apply Storage Blob Mock"""
    return EVENTBRITE_INSTANCES['get']
