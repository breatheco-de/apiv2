"""Requests mock."""

from .constants import (
    EVENTBRITE_ATTENDEE,
    EVENTBRITE_ATTENDEE_URL,
    EVENTBRITE_EVENT,
    EVENTBRITE_EVENT_URL,
    EVENTBRITE_ORDER,
    EVENTBRITE_ORDER_URL,
    EVENTBRITE_TICKET_CLASS,
    EVENTBRITE_TICKET_CLASS_URL,
)


class ResponseMock:
    """Simutate Response to be used by mocks."""

    status_code = None
    data = None
    content = None

    def __init__(self, status_code=200, data=""):
        self.status_code = status_code

        if isinstance(data, str):
            self.content = data
        else:
            self.data = data

    def json(self) -> dict:
        """Convert Response to JSON."""

        return self.data


def request_mock(url: str, auth=None, data=None, method=None, headers=None, params=None, json=None, timeout=30):
    """Requests get mock."""

    if url == EVENTBRITE_ORDER_URL:
        return ResponseMock(data=EVENTBRITE_ORDER, status_code=200)

    if url == EVENTBRITE_EVENT_URL:
        return ResponseMock(data=EVENTBRITE_EVENT, status_code=200)

    if url == EVENTBRITE_ATTENDEE_URL:
        return ResponseMock(data=EVENTBRITE_ATTENDEE, status_code=200)

    if url == EVENTBRITE_TICKET_CLASS_URL:
        return ResponseMock(data=EVENTBRITE_TICKET_CLASS, status_code=200)

    return ResponseMock(data={"ok": False, "status": "not found"}, status_code=404)
