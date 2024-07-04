"""
Mocks for `requests` module
"""

from .requests_mock import request_mock

# __all__ = [
#     'apply_requests_get_mock', 'apply_requests_post_mock', 'apply_requests_put_mock',
#     'apply_requests_delete_mock', 'apply_requests_request_mock', 'apply_requests_head_mock',
#     'apply_requests_patch_mock'
# ]

REQUESTS_PATH = {
    "get": "requests.get",
    "post": "requests.post",
    "put": "requests.put",
    "patch": "requests.patch",
    "delete": "requests.delete",
    "head": "requests.head",
    "request": "requests.request",
}

REQUESTS_INSTANCES = {
    "get": None,
    "post": None,
    "put": None,
    "patch": None,
    "delete": None,
    "head": None,
    "request": None,
}


def apply_requests_mock(method="get", endpoints=None):
    """Apply Storage Blob Mock"""

    if endpoints is None:
        endpoints = []

    method = method.lower()
    REQUESTS_INSTANCES[method] = request_mock(endpoints)
    return REQUESTS_INSTANCES[method]


def apply_requests_get_mock(endpoints=None):
    """
    Apply a mock to `requests.get`.

    Usage:

    ```py
    import requests
    from unittest.mock import patch, call
    from breathecode.tests.mocks import apply_requests_get_mock
    from breathecode.is_doesnt_exists import get_eventbrite_description_for_event

    @patch('requests.get', apply_requests_get_mock([
        200,
        'https://www.eventbriteapi.com/v3/events/1/structured_content/',
        { 'data': { ... } },
    ]))
    def test_xyz():
        get_eventbrite_descriptions_for_event(1)

        assert requests.get.call_args_list == [
            call('https://www.eventbriteapi.com/v3/events/1/structured_content/',
                headers={'Authorization': f'Bearer 1234567890'},
                data=None),
        ]
    ```
    """

    if endpoints is None:
        endpoints = []

    return apply_requests_mock("GET", endpoints)


def apply_requests_post_mock(endpoints=None):
    """
    Apply a mock to `requests.post`.

    Usage:

    ```py
    import requests
    from unittest.mock import patch, call
    from breathecode.tests.mocks import apply_requests_post_mock
    from breathecode.is_doesnt_exists import get_eventbrite_description_for_event

    @patch('requests.post', apply_requests_post_mock([
        201,
        'https://www.eventbriteapi.com/v3/events/1/structured_content/',
        { 'data': { ... } },
    ]))
    def test_xyz():
        post_eventbrite_descriptions_for_event(1)

        assert requests.post.call_args_list == [
            call('https://www.eventbriteapi.com/v3/events/1/structured_content/',
                headers={'Authorization': f'Bearer 1234567890'},
                data=None),
        ]
    ```
    """

    if endpoints is None:
        endpoints = []

    return apply_requests_mock("POST", endpoints)


def apply_requests_put_mock(endpoints=None):
    """
    Apply a mock to `requests.put`.

    Usage:

    ```py
    import requests
    from unittest.mock import patch, call
    from breathecode.tests.mocks import apply_requests_put_mock
    from breathecode.is_doesnt_exists import get_eventbrite_description_for_event

    @patch('requests.put', apply_requests_put_mock([
        200,
        'https://www.eventbriteapi.com/v3/events/1/structured_content/',
        { 'data': { ... } },
    ]))
    def test_xyz():
        put_eventbrite_descriptions_for_event(1)

        assert requests.put.call_args_list == [
            call('https://www.eventbriteapi.com/v3/events/1/structured_content/',
                headers={'Authorization': f'Bearer 1234567890'},
                data=None),
        ]
    ```
    """

    if endpoints is None:
        endpoints = []

    return apply_requests_mock("PUT", endpoints)


def apply_requests_patch_mock(endpoints=None):
    """
    Apply a mock to `requests.patch`.

    Usage:

    ```py
    import requests
    from unittest.mock import patch, call
    from breathecode.tests.mocks import apply_requests_patch_mock
    from breathecode.is_doesnt_exists import get_eventbrite_description_for_event

    @patch('requests.patch', apply_requests_patch_mock([
        200,
        'https://www.eventbriteapi.com/v3/events/1/structured_content/',
        None,
    ]))
    def test_xyz():
        patch_eventbrite_descriptions_for_event(1)

        assert requests.patch.call_args_list == [
            call('https://www.eventbriteapi.com/v3/events/1/structured_content/',
                headers={'Authorization': f'Bearer 1234567890'},
                data=None),
        ]
    ```
    """

    if endpoints is None:
        endpoints = []

    return apply_requests_mock("PATCH", endpoints)


def apply_requests_delete_mock(endpoints=None):
    """
    Apply a mock to `requests.delete`.

    Usage:

    ```py
    import requests
    from unittest.mock import patch, call
    from breathecode.tests.mocks import apply_requests_delete_mock
    from breathecode.is_doesnt_exists import get_eventbrite_description_for_event

    @patch('requests.delete', apply_requests_delete_mock([
        204,
        'https://www.eventbriteapi.com/v3/events/1/structured_content/',
        None,
    ]))
    def test_xyz():
        delete_eventbrite_descriptions_for_event(1)

        assert requests.delete.call_args_list == [
            call('https://www.eventbriteapi.com/v3/events/1/structured_content/',
                headers={'Authorization': f'Bearer 1234567890'},
                data=None),
        ]
    ```
    """

    if endpoints is None:
        endpoints = []

    return apply_requests_mock("DELETE", endpoints)


def apply_requests_head_mock(endpoints=None):
    """
    Apply a mock to `requests.head`.

    Usage:

    ```py
    import requests
    from unittest.mock import patch, call
    from breathecode.tests.mocks import apply_requests_head_mock
    from breathecode.is_doesnt_exists import get_eventbrite_description_for_event

    @patch('requests.head', apply_requests_head_mock([
        200,
        'https://www.eventbriteapi.com/v3/events/1/structured_content/',
        None,
    ]))
    def test_xyz():
        get_meta_for_eventbrite_description_for_event(1)

        assert requests.head.call_args_list == [
            call('https://www.eventbriteapi.com/v3/events/1/structured_content/',
                headers={'Authorization': f'Bearer 1234567890'},
                data=None),
        ]
    ```
    """

    if endpoints is None:
        endpoints = []

    return apply_requests_mock("HEAD", endpoints)


def apply_requests_request_mock(endpoints=None):
    """
    Apply a mock to `requests.request`.

    Usage:

    ```py
    import requests
    from unittest.mock import patch, call
    from breathecode.tests.mocks import apply_requests_request_mock
    from breathecode.is_doesnt_exists import get_eventbrite_description_for_event

    @patch('requests.request', apply_requests_request_mock([
        200,
        'https://www.eventbriteapi.com/v3/events/1/structured_content/',
        { 'data': { ... } },
    ]))
    def test_xyz():
        get_eventbrite_description_for_event(1)

        assert requests.request.call_args_list == [
            call('GET',
                'https://www.eventbriteapi.com/v3/events/1/structured_content/',
                headers={'Authorization': f'Bearer 1234567890'},
                data=None),
        ]
    ```
    """

    if endpoints is None:
        endpoints = []

    return apply_requests_mock("REQUEST", endpoints)
