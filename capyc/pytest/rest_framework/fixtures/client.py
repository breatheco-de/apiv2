"""
QuerySet fixtures.
"""

import pytest
from adrf.test import AsyncAPIClient as AsyncClient
from rest_framework.test import APIClient as Client

__all__ = ["client", "aclient", "Client", "AsyncClient"]


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def aclient():
    return AsyncClient()
