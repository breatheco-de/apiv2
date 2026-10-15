import pytest
from django.test import RequestFactory

from breathecode.utils.request import get_client_ip


@pytest.fixture(autouse=True)
def setup(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("TRUSTED_PROXY_COUNT", raising=False)
    yield


@pytest.mark.parametrize(
    "forwarded, proxies, expected",
    [
        ("203.0.113.7", None, "203.0.113.7"),
        # the client can prepend anything, the last entry is the one added by the router
        ("6.6.6.6, 203.0.113.7", None, "203.0.113.7"),
        ("6.6.6.6,203.0.113.7", "1", "203.0.113.7"),
        ("6.6.6.6, 203.0.113.7, 10.0.0.2", "2", "203.0.113.7"),
        ("203.0.113.7", "3", "203.0.113.7"),
        ("6.6.6.6, 203.0.113.7", "invalid", "203.0.113.7"),
    ],
)
def test_forwarded_for(monkeypatch: pytest.MonkeyPatch, forwarded, proxies, expected):
    if proxies is not None:
        monkeypatch.setenv("TRUSTED_PROXY_COUNT", proxies)

    request = RequestFactory().get("/", HTTP_X_FORWARDED_FOR=forwarded, REMOTE_ADDR="10.0.0.1")

    assert get_client_ip(request) == expected


def test_without_forwarded_for():
    assert get_client_ip(RequestFactory().get("/", REMOTE_ADDR="10.0.0.1")) == "10.0.0.1"
