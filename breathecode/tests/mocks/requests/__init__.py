"""
Google Cloud Storage Mocks
"""
from unittest.mock import Mock
from .requests_mock import request_mock

REQUESTS_PATH = {
    'get': 'requests.get',
    'post': 'requests.post',
    'put': 'requests.put',
    'patch': 'requests.patch',
    'delete': 'requests.delete',
    'head': 'requests.head',
}

REQUESTS_INSTANCES = {
    'get': None,
    'post': None,
    'put': None,
    'patch': None,
    'delete': None,
    'head': None,
}


def apply_requests_mock(method='get', endpoints=[]):
    """Apply Storage Blob Mock"""
    method = method.lower()
    REQUESTS_INSTANCES[method] = request_mock(endpoints)
    return REQUESTS_INSTANCES[method]


def apply_requests_get_mock(endpoints=[]):
    return apply_requests_mock('GET', endpoints)


def apply_requests_post_mock(endpoints=[]):
    return apply_requests_mock('POST', endpoints)


def apply_requests_put_mock(endpoints=[]):
    return apply_requests_mock('PUT', endpoints)


def apply_requests_patch_mock(endpoints=[]):
    return apply_requests_mock('PATCH', endpoints)


def apply_requests_delete_mock(endpoints=[]):
    return apply_requests_mock('DELETE', endpoints)


def apply_requests_head_mock(endpoints=[]):
    return apply_requests_mock('HEAD', endpoints)
