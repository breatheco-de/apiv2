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

    assert call_args[1] == "form.html"
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

    assert call_args[1] == "form.html"
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
    token, created = Token.get_or_create(model.user, token_type="temporal")

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
    token, created = Token.get_or_create(model.user, token_type="temporal")

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
        "callback": "https://naturo.io/",
    }
    response = client.post(url, data)

    assert isinstance(response, HttpResponseRedirect)
    assert response.url == "https://naturo.io/?msg=Check%20your%20email%20for%20a%20password%20reset!"
    assert response.status_code == status.HTTP_302_FOUND
    assert database.list_of("auth.User") == []
    mock_notify_email_message.assert_not_called()


def test_password_reset__post__with_callback__with_email__with_user(client, mock_notify_email_message, database):
    """Test POST /password/reset with callback and email for existing user. Expects 302 Redirect and email sent."""
    url = reverse_lazy("authenticate:password_reset")
    model = database.create(user=1)
    data = {
        "email": model.user.email,
        "callback": "https://naturo.io/",
    }
    response = client.post(url, data)
    token, created = Token.get_or_create(model.user, token_type="temporal")

    assert isinstance(response, HttpResponseRedirect)
    assert response.url == "https://naturo.io/?msg=Check%20your%20email%20for%20a%20password%20reset!"
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
        "callback": "https://naturo.io/",
    }
    response = client.post(url, data)
    token, created = Token.get_or_create(model.user, token_type="temporal")

    assert isinstance(response, HttpResponseRedirect)
    assert response.url == "https://naturo.io/?msg=Check%20your%20email%20for%20a%20password%20reset!"
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
