"""
QuerySet fixtures.
"""

from typing import Generator, final

import pytest
from django.db.models.query import QuerySet
from rest_framework.test import APIClient as Client

__all__ = ['client', 'Client']


@pytest.fixture
def client():
    return Client()
