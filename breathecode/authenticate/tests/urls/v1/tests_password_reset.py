"""
Test cases for /user
"""

import os
from unittest.mock import MagicMock, call

import pytest  # Import pytest
from django.http import HttpResponse, HttpResponseRedirect  # Import for checking redirects
from django.urls.base import reverse_lazy
from rest_framework import status

from breathecode.authenticate.models import Token


@pytest.fixture(autouse=True)
def setup(db):
    pass


# Fixture for the notify mock
@pytest.fixture
def mock_notify_email_message(monkeypatch):
    mock = MagicMock()
    monkeypatch.setattr("breathecode.notify.actions.send_email_message", mock)
    return mock


# Fixture for the messages mock
@pytest.fixture
def mock_django_messages(monkeypatch):
    mock = MagicMock()
    monkeypatch.setattr("breathecode.authenticate.views.messages", mock)
    return mock


# Fixture for the render mock
@pytest.fixture
def mock_django_render(monkeypatch):
    mock = MagicMock(return_value=HttpResponse(""))
    monkeypatch.setattr("django.shortcuts.render", mock)
    return mock


# Test functions start here, outside of any class


def test_password_reset__post__without_email(
    client, mock_django_render, mock_django_messages, mock_notify_email_message
):
    """Test POST /password/reset without providing an email. Expects a 200 OK with form.html rendered and an error message."""
    url = reverse_lazy("authenticate:password_reset")
    data = {}  # No email provided
    response = client.post(url, data)

    mock_django_render.assert_called_once()
    call_args, call_kwargs = mock_django_render.call_args
    context = call_kwargs.get("context") or (call_args[2] if len(call_args) > 2 else None)

    assert call_args[1] == "reset_password.html"
    assert context["form"].errors
    mock_django_messages.error.assert_called_once_with(call_args[0], "Email is required")  # Check request and message

    assert response.status_code == status.HTTP_200_OK
    mock_notify_email_message.assert_not_called()


def test_password_reset__post__with_invalid_email_format(
    client, mock_django_render, mock_django_messages, mock_notify_email_message
):
    """Test POST /password/reset with an invalid email format. Expects a 200 OK with form.html rendered and an error message."""
    url = reverse_lazy("authenticate:password_reset")
    data = {"email": "invalid-email"}
    response = client.post(url, data)

    mock_django_render.assert_called_once()
    call_args, call_kwargs = mock_django_render.call_args
    context = call_kwargs.get("context") or (call_args[2] if len(call_args) > 2 else None)

    assert call_args[1] == "reset_password.html"
    assert context["form"].errors
    mock_django_messages.error.assert_called_once_with(call_args[0], "Invalid email format.")

    assert response.status_code == status.HTTP_200_OK
    mock_notify_email_message.assert_not_called()


def test_password_reset__post__with_email__user_not_found(
    client, mock_django_render, mock_notify_email_message, database
):
    """Test POST /password/reset with a valid email for a non-existent user. Expects 200 OK with message.html rendered, but no email sent."""
    url = reverse_lazy("authenticate:password_reset")
    data = {"email": "konan@naturo.io"}
    response = client.post(url, data)

    mock_django_render.assert_called_once()
    call_args, call_kwargs = mock_django_render.call_args
    context = call_kwargs.get("context") or (call_args[2] if len(call_args) > 2 else None)

    assert call_args[1] == "message.html"
    assert context["MESSAGE"] == "Check your email for a password reset!"

    assert response.status_code == status.HTTP_200_OK
    assert database.list_of("auth.User") == []
    mock_notify_email_message.assert_not_called()


def test_password_reset__post__with_email__with_user(client, mock_django_render, mock_notify_email_message, database):
    """Test POST /password/reset with a valid email for an existing user. Expects 200 OK with message.html rendered and reset email sent."""
    url = reverse_lazy("authenticate:password_reset")
    model = database.create(user=1)
    data = {"email": model.user.email}
    response = client.post(url, data)
    token, created = Token.get_or_create(model.user, token_type="short")

    mock_django_render.assert_called_once()
    call_args, call_kwargs = mock_django_render.call_args
    context = call_kwargs.get("context") or (call_args[2] if len(call_args) > 2 else None)

    assert call_args[1] == "message.html"
    assert context["MESSAGE"] == "Check your email for a password reset!"

    assert response.status_code == status.HTTP_200_OK
    db_users = database.list_of("auth.User")
    assert len(db_users) == 1
    assert db_users[0]["id"] == model.user.id
    assert db_users[0]["email"] == model.user.email

    assert mock_notify_email_message.call_args_list == [
        call(
            "pick_password",
            model.user.email,
            {
                "SUBJECT": "You asked to reset your password at 4Geeks",
                "LINK": os.getenv("API_URL", "") + f"/v1/auth/password/{token}",
            },
            academy=None,
        )
    ]


def test_password_reset__post__with_email_in_uppercase__with_user(
    client, mock_django_render, mock_notify_email_message, database
):
    """Test POST /password/reset with an existing user's email in uppercase. Expects 200 OK, message.html, and email sent."""
    url = reverse_lazy("authenticate:password_reset")
    model = database.create(user=1)
    data = {"email": model.user.email.upper()}
    response = client.post(url, data)
    token, created = Token.get_or_create(model.user, token_type="short")

    mock_django_render.assert_called_once()
    call_args, call_kwargs = mock_django_render.call_args
    context = call_kwargs.get("context") or (call_args[2] if len(call_args) > 2 else None)

    assert call_args[1] == "message.html"
    assert context["MESSAGE"] == "Check your email for a password reset!"

    assert response.status_code == status.HTTP_200_OK
    db_users = database.list_of("auth.User")
    assert len(db_users) == 1
    assert db_users[0]["id"] == model.user.id
    assert db_users[0]["email"] == model.user.email

    assert mock_notify_email_message.call_args_list == [
        call(
            "pick_password",
            model.user.email,
            {
                "SUBJECT": "You asked to reset your password at 4Geeks",
                "LINK": os.getenv("API_URL", "") + f"/v1/auth/password/{token}",
            },
            academy=None,
        )
    ]


# Redirect tests


def test_password_reset__post__with_callback__with_email__user_not_found(client, mock_notify_email_message, database):
    """Test POST /password/reset with callback and email for non-existent user. Expects 302 Redirect, no email sent."""
    url = reverse_lazy("authenticate:password_reset")
    data = {
        "email": "konan@naturo.io",
        "callback": "https://4geeks.com/",
    }
    response = client.post(url, data)

    assert isinstance(response, HttpResponseRedirect)
    assert response.url == "https://4geeks.com/?msg=Check%20your%20email%20for%20a%20password%20reset!"
    assert response.status_code == status.HTTP_302_FOUND
    assert database.list_of("auth.User") == []
    mock_notify_email_message.assert_not_called()


def test_password_reset__post__with_callback__with_email__with_user(client, mock_notify_email_message, database):
    """Test POST /password/reset with callback and email for existing user. Expects 302 Redirect and email sent."""
    url = reverse_lazy("authenticate:password_reset")
    model = database.create(user=1)
    data = {
        "email": model.user.email,
        "callback": "https://4geeks.com/",
    }
    response = client.post(url, data)
    token, created = Token.get_or_create(model.user, token_type="short")

    assert isinstance(response, HttpResponseRedirect)
    assert response.url == "https://4geeks.com/?msg=Check%20your%20email%20for%20a%20password%20reset!"
    assert response.status_code == status.HTTP_302_FOUND
    db_users = database.list_of("auth.User")
    assert len(db_users) == 1
    assert db_users[0]["id"] == model.user.id
    assert db_users[0]["email"] == model.user.email

    assert mock_notify_email_message.call_args_list == [
        call(
            "pick_password",
            model.user.email,
            {
                "SUBJECT": "You asked to reset your password at 4Geeks",
                "LINK": os.getenv("API_URL", "") + f"/v1/auth/password/{token}",
            },
            academy=None,
        )
    ]


def test_password_reset__post__with_callback__with_email_in_uppercase__with_user(
    client, mock_notify_email_message, database
):
    """Test POST /password/reset with callback and uppercase email for existing user. Expects 302 Redirect and email sent."""
    url = reverse_lazy("authenticate:password_reset")
    model = database.create(user=1)
    data = {
        "email": model.user.email.upper(),
        "callback": "https://4geeks.com/",
    }
    response = client.post(url, data)
    token, created = Token.get_or_create(model.user, token_type="short")

    assert isinstance(response, HttpResponseRedirect)
    assert response.url == "https://4geeks.com/?msg=Check%20your%20email%20for%20a%20password%20reset!"
    assert response.status_code == status.HTTP_302_FOUND
    db_users = database.list_of("auth.User")
    assert len(db_users) == 1
    assert db_users[0]["id"] == model.user.id
    assert db_users[0]["email"] == model.user.email

    assert mock_notify_email_message.call_args_list == [
        call(
            "pick_password",
            model.user.email,
            {
                "SUBJECT": "You asked to reset your password at 4Geeks",
                "LINK": os.getenv("API_URL", "") + f"/v1/auth/password/{token}",
            },
            academy=None,
        )
    ]


@pytest.mark.parametrize("param", ["callback", "url"])
def test_password_reset__get__with_callback_not_allowed(client, param):
    """Test GET /password/reset with a foreign callback. Expects 400 and no form."""
    url = reverse_lazy("authenticate:password_reset") + f"?{param}=https://evil.com/"
    response = client.get(url)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert b"The redirect url is not allowed" in response.content


def test_password_reset__post__with_callback_not_allowed(client, mock_notify_email_message, database):
    """Test POST /password/reset with a foreign callback. Expects 400 and no email sent."""
    url = reverse_lazy("authenticate:password_reset")
    model = database.create(user=1)
    data = {
        "email": model.user.email,
        "callback": "https://evil.com/",
    }
    response = client.post(url, data)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert b"The redirect url is not allowed" in response.content
    mock_notify_email_message.assert_not_called()


def test_password_reset__post__email_limit_is_silent(client, mock_notify_email_message, database):
    """After 3 requests for the same email the response is unchanged but no more emails are sent."""
    url = reverse_lazy("authenticate:password_reset")
    model = database.create(user=1)
    data = {"email": model.user.email, "callback": "https://4geeks.com/"}

    responses = [client.post(url, data) for _ in range(4)]

    assert [x.status_code for x in responses] == [status.HTTP_302_FOUND] * 4
    assert len({x.url for x in responses}) == 1
    assert mock_notify_email_message.call_count == 3


def test_password_reset__post__ip_limit(client, mock_notify_email_message, database):
    """After 10 requests from the same IP the endpoint answers 429."""
    url = reverse_lazy("authenticate:password_reset")

    for i in range(10):
        response = client.post(url, {"email": f"user{i}@naturo.io"}, REMOTE_ADDR="203.0.113.7")
        assert response.status_code == status.HTTP_200_OK

    response = client.post(url, {"email": "user11@naturo.io"}, REMOTE_ADDR="203.0.113.7")

    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert response["Retry-After"] == "3600"


def test_password_reset__post__rate_limit_disabled_scope(client, mock_notify_email_message, database, monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_DISABLED_SCOPES", "password-reset")
    url = reverse_lazy("authenticate:password_reset")
    model = database.create(user=1)

    for _ in range(4):
        client.post(url, {"email": model.user.email})

    assert mock_notify_email_message.call_count == 4
