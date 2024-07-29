class FakeResponse:
    """Simutate Response to be used by mocks"""

    status_code = 200
    data = {}

    def __init__(self, status_code, data, timeout=None):
        self.data = data
        self.status_code = status_code

    def json(self):
        """Convert Response to JSON"""
        return self.data
