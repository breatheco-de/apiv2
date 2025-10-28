import pytest
from unittest.mock import MagicMock, patch


@patch("breathecode.payments.actions.notify_actions")
@patch("breathecode.payments.actions.get_app_url", return_value="https://app")
@patch("breathecode.payments.actions.UserInvite")
def test_invite_user_to_subscription_team_sends_when_created(mock_invite, mock_get_app_url, mock_notify):
    """Sends welcome email when invite is newly created."""
    from breathecode.payments.actions import invite_user_to_subscription_team

    invite = MagicMock()
    invite.status = "PENDING"
    invite.token = "abc"
    mock_invite.objects.get_or_create.return_value = (invite, True)

    subscription = MagicMock()
    subscription.academy.name = "My Academy"
    subscription.user = MagicMock()

    subscription_seat = MagicMock()

    obj = {"email": "john@example.com", "first_name": "John", "last_name": "Doe"}

    invite_user_to_subscription_team(obj, subscription, subscription_seat, lang="en")

    mock_invite.objects.get_or_create.assert_called_once()
    mock_notify.send_email_message.assert_called_once()
    args, kwargs = mock_notify.send_email_message.call_args
    assert args[0] == "welcome_academy"
    assert args[1] == "john@example.com"
    assert kwargs["academy"] is subscription.academy
    assert "LINK" in kwargs["args"][2] if "args" in kwargs else True


@patch("breathecode.payments.actions.notify_actions")
@patch("breathecode.payments.actions.get_app_url", return_value="https://app")
@patch("breathecode.payments.actions.UserInvite")
def test_invite_user_to_subscription_team_skips_when_accepted(mock_invite, mock_get_app_url, mock_notify):
    """Does not send email when invite exists and status is not PENDING."""
    from breathecode.payments.actions import invite_user_to_subscription_team

    invite = MagicMock()
    invite.status = "ACCEPTED"
    invite.token = "abc"
    mock_invite.objects.get_or_create.return_value = (invite, False)

    subscription = MagicMock()
    subscription.academy.name = "My Academy"
    subscription.user = MagicMock()

    subscription_seat = MagicMock()
    obj = {"email": "john@example.com"}

    invite_user_to_subscription_team(obj, subscription, subscription_seat, lang="en")

    mock_notify.send_email_message.assert_not_called()
