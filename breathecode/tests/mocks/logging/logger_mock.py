"""
Requests mock
"""

class LoggerMock():
    """Simutate Response to be used by mocks"""
    status_code = None
    data = None
    content = None

    def __init__(self, *args, **wargs):
        pass

    def debug(self, *args, **kwargs) -> dict:
        """Convert Response to JSON"""
        return self.data

def logger_mock(*args, **wargs):
    """Requests get mock"""
    return LoggerMock(*args, **wargs)
