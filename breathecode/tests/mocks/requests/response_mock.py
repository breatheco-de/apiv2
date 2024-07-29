import json


class ResponseMock:
    """Simutate Response to be used by mocks."""

    status_code = None
    reason = None
    data = None
    content = None
    raw = None
    url = None
    headers = {
        "Content-Type": "application/json",
        "content-type": "application/json",
    }

    def __init__(self, status_code=200, data="", url="", request_headers=None):
        self.status_code = status_code
        self.reason = "OK"
        self.raw = data
        self.url = url
        self.headers = (
            request_headers
            if request_headers is not None
            else {
                "Content-Type": "application/json",
                "content-type": "application/json",
            }
        )

        if isinstance(data, str):
            self.content = str(data).encode("utf-8")
            self.text = data
        else:
            content = json.dumps(data)

            self.data = data
            self.text = content
            self.content = content.encode("utf-8")

    def json(self) -> dict:
        """Convert Response to JSON."""
        return self.data
