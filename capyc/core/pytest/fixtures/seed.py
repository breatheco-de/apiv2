import random
from typing import Generator, Optional

import pytest

__all__ = ["seed", "Seed", "pytest_addoption", "pytest_terminal_summary"]

type Seed = Optional[int]
SEED = random.randint(0, 2**32 - 1)
seed_used = None
SEED_KEY = "_+* SEED *+_"
END_KEY = "_+* END *+_"


def pytest_addoption(parser: pytest.Parser):
    try:
        parser.addoption("--seed", action="store", default=None, type=int, help="Set the random seed for tests")
    except Exception:
        ...


def pytest_terminal_summary(terminalreporter, config: pytest.Config) -> None:
    ...
    # if hasattr(config, END_KEY) is False:
    #     setattr(config, END_KEY, True)
    #     seed = getattr(config, SEED_KEY, None)
    #     terminalreporter.write_sep("=", "Capy Core Summary")
    #     terminalreporter.write_line(f"Seed: {seed}")


@pytest.fixture(autouse=True)
def seed(request: pytest.FixtureRequest) -> Generator[Optional[int], None, None]:
    global SEED

    seed = request.config.getoption("--seed")
    if seed is None:
        seed = SEED

    # if hasattr(request.config, SEED_KEY) is False:
    #     setattr(request.config, SEED_KEY, seed)

    yield seed
    print(f"Seed used: {seed}")
