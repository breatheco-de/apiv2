"""Requests mock."""

from .constants import CONTACT_AUTOMATIONS, CONTACT_AUTOMATIONS_URL, OLD_BREATHECODE_ADMIN, OLD_BREATHECODE_ADMIN_URL


class ResponseMock:
    """Simutate Response to be used by mocks."""

    status_code = None
    data = None
    content = None
    headers = {
        "Content-Type": "application/json",
    }

    def __init__(self, status_code=200, data=""):
        self.status_code = status_code

        if isinstance(data, str):
            self.content = data
        else:
            self.data = data

    def json(self) -> dict:
        """Convert Response to JSON."""
        return self.data


def request_mock(method: str, url: str, auth=None, data=None, headers=None, params=None, json=None, timeout=30):
    """Requests get mock."""
    if url == OLD_BREATHECODE_ADMIN_URL:
        return ResponseMock(data=OLD_BREATHECODE_ADMIN, status_code=200)

    if url == CONTACT_AUTOMATIONS_URL:
        return ResponseMock(data=CONTACT_AUTOMATIONS, status_code=200)

    return ResponseMock(data={"ok": False, "status": "not found"}, status_code=404)
