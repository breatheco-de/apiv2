"""
QuerySet fixtures.
"""

import pytest
from rest_framework.test import APIClient as Client

__all__ = ["client", "Client"]


@pytest.fixture
def client():
    return Client()
