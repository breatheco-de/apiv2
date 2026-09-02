"""
Test cases for GET/POST /v1/auth/view/login (hosted HTML login).
"""

from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth.hashers import make_password
from django.http import HttpResponseRedirect
from django.urls.base import reverse_lazy
from rest_framework import status

@pytest.fixture(autouse=True)
def setup(db, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APPLY_CAPTCHA", "FALSE")
    monkeypatch.setenv("LOGIN_RATE_LIMIT_ENABLED", "FALSE")
    yield


def test_login_view__get__without_url(client):
    url = reverse_lazy("authenticate:login_view")
    response = client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert b"You must specify a &#x27;url&#x27;" in response.content or b"You must specify a 'url'" in response.content


def test_login_view__get__with_url(client):
    url = reverse_lazy("authenticate:login_view") + "?url=https://example.com/callback"
    response = client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert b"cf-turnstile" not in response.content
    assert b'name="email"' in response.content
    assert b'name="password"' in response.content


def test_login_view__get__with_captcha_enabled(client, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APPLY_CAPTCHA", "TRUE")
    monkeypatch.setenv("CLOUDFLARE_TURNSTILE_SITE_KEY", "test-site-key")

    url = reverse_lazy("authenticate:login_view") + "?url=https://example.com/callback"
    response = client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert b"cf-turnstile" in response.content
    assert b"test-site-key" in response.content
    assert b"challenges.cloudflare.com/turnstile/v0/api.js" in response.content


def test_login_view__post__success(client, database):
    password = "Pain!$%"
    user = {"email": "konan@naruto.io", "password": make_password(password)}
    user_invite = {"email": "konan@naruto.io", "status": "ACCEPTED", "is_email_validated": True}
    model = database.create(user=user, user_invite=user_invite)

    url = reverse_lazy("authenticate:login_view")
    response = client.post(
        url,
        {
            "email": model.user.email,
            "password": password,
            "url": "https://example.com/callback",
        },
    )

    assert response.status_code == status.HTTP_302_FOUND
    assert isinstance(response, HttpResponseRedirect)
    assert response.url.startswith("https://example.com/callback?")
    assert "token=" in response.url
    assert "attempt=1" in response.url


def test_login_view__post__bad_credentials(client, database):
    password = "Pain!$%"
    user = {"email": "konan@naruto.io", "password": make_password(password)}
    user_invite = {"email": "konan@naruto.io", "status": "ACCEPTED", "is_email_validated": True}
    model = database.create(user=user, user_invite=user_invite)

    url = reverse_lazy("authenticate:login_view")
    response = client.post(
        url,
        {
            "email": model.user.email,
            "password": "wrong-password",
            "url": "https://example.com/callback",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert b"Unable to log in with provided credentials." in response.content


@patch(
    "breathecode.authenticate.utils.login_protection.Turnstile.verify_token",
    MagicMock(side_effect=Exception("should not be called")),
)
def test_login_view__post__captcha_disabled_skips_turnstile(client, database):
    password = "Pain!$%"
    user = {"email": "konan@naruto.io", "password": make_password(password)}
    user_invite = {"email": "konan@naruto.io", "status": "ACCEPTED", "is_email_validated": True}
    model = database.create(user=user, user_invite=user_invite)

    url = reverse_lazy("authenticate:login_view")
    response = client.post(
        url,
        {
            "email": model.user.email,
            "password": password,
            "url": "https://example.com/callback",
        },
    )

    assert response.status_code == status.HTTP_302_FOUND


def test_login_view__post__captcha_enabled_missing_token(client, database, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APPLY_CAPTCHA", "TRUE")
    monkeypatch.setenv("CLOUDFLARE_TURNSTILE_SECRET_KEY", "test-secret")

    password = "Pain!$%"
    user = {"email": "konan@naruto.io", "password": make_password(password)}
    user_invite = {"email": "konan@naruto.io", "status": "ACCEPTED", "is_email_validated": True}
    model = database.create(user=user, user_invite=user_invite)

    url = reverse_lazy("authenticate:login_view")
    response = client.post(
        url,
        {
            "email": model.user.email,
            "password": password,
            "url": "https://example.com/callback",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert b"Missing Turnstile token" in response.content or b"Turnstile" in response.content


def test_login_view__post__captcha_enabled_with_mocked_verify(client, database, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APPLY_CAPTCHA", "TRUE")
    monkeypatch.setenv("CLOUDFLARE_TURNSTILE_SECRET_KEY", "test-secret")

    password = "Pain!$%"
    user = {"email": "konan@naruto.io", "password": make_password(password)}
    user_invite = {"email": "konan@naruto.io", "status": "ACCEPTED", "is_email_validated": True}
    model = database.create(user=user, user_invite=user_invite)

    with patch(
        "breathecode.authenticate.utils.login_protection.Turnstile.verify_token",
        MagicMock(return_value={"success": True}),
    ) as mock_verify:
        url = reverse_lazy("authenticate:login_view")
        response = client.post(
            url,
            {
                "email": model.user.email,
                "password": password,
                "url": "https://example.com/callback",
                "cf-turnstile-response": "fake-token",
            },
        )

        mock_verify.assert_called_once()
        assert response.status_code == status.HTTP_302_FOUND
        assert "token=" in response.url


def test_login_view__post__rate_limited(client, database, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("LOGIN_RATE_LIMIT_ENABLED", "TRUE")
    monkeypatch.setenv("LOGIN_RATE_LIMIT_MAX_ATTEMPTS", "2")
    monkeypatch.setenv("LOGIN_RATE_LIMIT_WINDOW_SECONDS", "900")

    password = "Pain!$%"
    user = {"email": "konan@naruto.io", "password": make_password(password)}
    user_invite = {"email": "konan@naruto.io", "status": "ACCEPTED", "is_email_validated": True}
    model = database.create(user=user, user_invite=user_invite)

    url = reverse_lazy("authenticate:login_view")
    payload = {
        "email": model.user.email,
        "password": "wrong-password",
        "url": "https://example.com/callback",
    }

    assert client.post(url, payload).status_code == status.HTTP_200_OK
    assert client.post(url, payload).status_code == status.HTTP_200_OK

    response = client.post(url, payload)
    assert response.status_code == status.HTTP_200_OK
    assert b"Too many login attempts" in response.content
