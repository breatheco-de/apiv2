"""Tests for the client-supplied redirect url allowlist."""

import base64

import capyc.pytest as capy
import pytest
from capyc.rest_framework.exceptions import ValidationException

from breathecode.authenticate.receivers import clear_academy_redirect_hosts
from breathecode.authenticate.utils.redirects import (
    decode_redirect_url,
    is_allowed_redirect_url,
    validate_redirect_url,
)


@pytest.fixture(autouse=True)
def setup(db, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("SITE_URL", raising=False)
    monkeypatch.delenv("APP_URL", raising=False)
    monkeypatch.delenv("API_URL", raising=False)
    yield


@pytest.mark.parametrize(
    "url",
    [
        "https://4geeks.com",
        "https://4geeks.com/login?next=/dashboard",
        "https://app.4geeks.com/callback",
        "https://deep.sub.4geeks.com/callback",
        "https://4geeksacademy.com/es/inicio",
        "https://www.4geeksacademy.com",
        "https://learnpack.co/start",
        "https://editor.learnpack.co",
        "https://4GEEKS.com/upper",
        "https://4geeks.com:8443/port",
        "/relative/path",
        "/1337?next=/home",
    ],
)
def test_allowed(url):
    assert is_allowed_redirect_url(url) is True


@pytest.mark.parametrize("url", ["http://localhost:3000/callback", "http://127.0.0.1:8000/callback"])
def test_http_localhost_allowed_in_debug(url, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("django.conf.settings.DEBUG", True)

    assert is_allowed_redirect_url(url) is True


@pytest.mark.parametrize(
    "url",
    [
        None,
        "",
        "relative/path",
        "//evil.com",
        "///evil.com",
        "/\\evil.com",
        "/\\/evil.com",
        "javascript:alert(1)",
        "data:text/html,hi",
        "ftp://4geeks.com",
        "http://4geeks.com",
        "https://evil.com",
        "https://evil4geeks.com",
        "https://4geeks.com.evil.com",
        "https://4geeks.co",
        "https://learnpack.co.evil.com",
        "https://4geeks.com@evil.com",
        "https://4geeks.com\\@evil.com",
        "https:\\\\evil.com",
        "https://evil.com/?r=https://4geeks.com",
        "https://evil.com#4geeks.com",
        "https://4geeks.com\n.evil.com",
    ],
)
def test_rejected(url):
    assert is_allowed_redirect_url(url) is False


def test_http_localhost_rejected_outside_debug(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("django.conf.settings.DEBUG", False)

    assert is_allowed_redirect_url("http://localhost:3000/callback") is False
    assert is_allowed_redirect_url("https://4geeks.com") is True


def test_env_hosts_are_exact_matches(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SITE_URL", "https://my-site.example")
    monkeypatch.setenv("APP_URL", "https://my-app.example/")
    monkeypatch.setenv("API_URL", "https://my-api.example")

    assert is_allowed_redirect_url("https://my-site.example/path") is True
    assert is_allowed_redirect_url("https://my-app.example/path") is True
    assert is_allowed_redirect_url("https://my-api.example/v1/auth/view/login") is True
    assert is_allowed_redirect_url("https://sub.my-site.example/path") is False


def test_academy_hosts_are_exact_matches(database: capy.Database):
    database.create(
        academy={"website_url": "https://white-label.example", "white_label_url": "https://portal.other.example/app"},
        city=1,
        country=1,
    )

    assert is_allowed_redirect_url("https://white-label.example/accept-invite") is True
    assert is_allowed_redirect_url("https://portal.other.example/login") is True
    assert is_allowed_redirect_url("https://sub.white-label.example") is False


def test_academy_hosts_cache_is_invalidated(database: capy.Database):
    assert is_allowed_redirect_url("https://new-academy.example") is False

    database.create(academy={"website_url": "https://new-academy.example"}, city=1, country=1)

    # the host list is cached until an academy is saved or deleted
    assert is_allowed_redirect_url("https://new-academy.example") is False

    clear_academy_redirect_hosts(sender=None)

    assert is_allowed_redirect_url("https://new-academy.example") is True


def test_validate_redirect_url():
    assert validate_redirect_url("https://4geeks.com") == "https://4geeks.com"

    with pytest.raises(ValidationException, match="invalid-redirect-url"):
        validate_redirect_url("https://evil.com")


def test_decode_redirect_url():
    encoded = base64.b64encode(b"https://4geeks.com/callback").decode("utf-8")

    assert decode_redirect_url(encoded) == "https://4geeks.com/callback"
    assert decode_redirect_url("https://4geeks.com/callback") == "https://4geeks.com/callback"
    assert decode_redirect_url(None) is None
