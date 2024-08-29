import pytest

__all__ = ["disable_newrelic_prints"]


@pytest.fixture(autouse=True)
def disable_newrelic_prints(monkeypatch: pytest.MonkeyPatch):
    """Disable NewRelic prints."""

    monkeypatch.setattr("newrelic.core.agent._logger.info", lambda *args, **kwargs: None)
    monkeypatch.setattr("newrelic.core.agent._logger.warn", lambda *args, **kwargs: None)
    monkeypatch.setattr("newrelic.core.agent._logger.error", lambda *args, **kwargs: None)

    yield
