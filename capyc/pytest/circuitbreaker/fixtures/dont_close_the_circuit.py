from typing import Generator
from unittest.mock import patch

import pytest

__all__ = ["dont_close_the_circuit"]


@pytest.fixture(autouse=True)
def dont_close_the_circuit() -> Generator[None, None, None]:
    """Don't allow the circuit be closed."""

    with patch("circuitbreaker.CircuitBreaker._failure_count", 0, create=True):
        with patch("circuitbreaker.CircuitBreaker.FAILURE_THRESHOLD", 10000000, create=True):
            yield
