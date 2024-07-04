"""Requests mock."""


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

    return ResponseMock(data={"ok": True}, status_code=200)
