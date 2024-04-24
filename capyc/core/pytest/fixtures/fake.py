from typing import Generator

import pytest
from faker import Faker as Fake

__all__ = ['fake', 'Fake']

FAKE = Fake()


@pytest.fixture(scope='module')
def fake() -> Generator[Fake, None, None]:
    return FAKE
