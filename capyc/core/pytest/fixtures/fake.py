from typing import Generator, Optional

import pytest
from faker import Faker as Fake

__all__ = ["fake", "Fake"]


@pytest.fixture(autouse=True)
def fake(seed: Optional[int]) -> Generator[Fake, None, None]:
    f = Fake()
    f.seed_instance(seed)

    yield f
