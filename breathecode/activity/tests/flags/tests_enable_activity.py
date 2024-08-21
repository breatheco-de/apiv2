import pytest

from capyc.core.managers import feature


def test_activity_is_none() -> None:
    value = feature.is_enabled("activity.logs")
    assert value is True


@pytest.mark.parametrize("env", feature.FALSE)
def test_activity_is_false(monkeypatch: pytest.MonkeyPatch, env: str) -> None:
    monkeypatch.setenv("ENABLE_ACTIVITY", env)
    value = feature.is_enabled("activity.logs")
    assert value is False


@pytest.mark.parametrize("env", feature.TRUE)
def test_activity_is_true(monkeypatch: pytest.MonkeyPatch, env: str) -> None:
    monkeypatch.setenv("ENABLE_ACTIVITY", env)
    value = feature.is_enabled("activity.logs")
    assert value is True
