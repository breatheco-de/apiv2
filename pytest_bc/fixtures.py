from typing import Generator

import pytest
from faker import Faker

FAKE = Faker()


@pytest.fixture(scope='module')
def fake() -> Generator[Faker, None, None]:
    return FAKE
