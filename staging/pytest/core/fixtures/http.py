import pytest
from typing import Generator
from aioresponses import aioresponses
import requests_mock

__all__ = ["aiohttp", "requests", "AIOHTTP", "Requests"]

AIOHTTP = aioresponses
Requests = requests_mock.Mocker


# Fixture for mocking aiohttp requests
@pytest.fixture
def aiohttp() -> Generator[aioresponses, None, None]:
    with aioresponses() as m:
        yield m


# Fixture for mocking requests
@pytest.fixture
def requests() -> Generator[requests_mock.Mocker, None, None]:
    with requests_mock.Mocker() as m:
        yield m
