from unittest.mock import Mock

def requests_mock(routes: dict, method='get'):
    """Arequests mock"""
    if method == 'get':
        def side_effect (url, headers=None):
            return routes.get(url, f'unhandled request {url}')
    elif method == 'post':
        def side_effect (url, data=None, headers=None):
            return routes.get(url, f'unhandled request {url}')
    else:
        raise Exception(f'{method} are not implemented too')
    return Mock(side_effect=side_effect)


class FakeResponse():
    """Simutate Response to be used by mocks"""
    status_code = 200
    data = {}

    def __init__(self, status_code, data):
        self.data = data
        self.status_code = status_code

    def json(self):
        """Convert Response to JSON"""
        return self.data


class FakeHtmlResponse():
    """Simutate Response to be used by mocks"""
    status_code = 200
    content = ''

    def __init__(self, status_code, content):
        self.content = content
        self.status_code = status_code
