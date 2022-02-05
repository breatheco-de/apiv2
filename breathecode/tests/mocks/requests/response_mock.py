import json


class ResponseMock():
    """Simutate Response to be used by mocks"""
    status_code = None
    reason = None
    data = None
    content = None
    raw = None
    url = None
    headers = {
        'Content-Type': 'application/json',
        'content-type': 'application/json',
    }

    def __init__(self, status_code=200, data='', url=''):
        self.status_code = status_code
        self.reason = 'OK'
        self.raw = data
        self.url = url

        if isinstance(data, str):
            self.content = data
            self.text = data
        else:
            content = json.dumps(data)

            self.data = data
            self.text = content
            self.content = content.encode('utf-8')

    def json(self) -> dict:
        """Convert Response to JSON"""
        return self.data
