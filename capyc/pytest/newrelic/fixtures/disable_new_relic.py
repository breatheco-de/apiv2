from typing import Generator

import pytest

__all__ = ["disable_new_relic"]


@pytest.fixture(autouse=True)
def disable_new_relic(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setattr("newrelic.core.agent.Agent._atexit_shutdown", lambda *args, **kwargs: None)
