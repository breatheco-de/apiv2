from unittest.mock import MagicMock, patch

import capyc.pytest as capy
import pytest

from breathecode.assignments.models import RepositoryDeletionOrder
from breathecode.assignments.receivers import repository_deletion_order_status_updated
from breathecode.authenticate.models import CredentialsGithub
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode


@pytest.fixture
def mock_send_email_message(monkeypatch):
    mock = MagicMock()
    monkeypatch.setattr("breathecode.assignments.receivers.send_email_message", mock)
    return mock


@pytest.mark.parametrize(
    "from_status, to_status, provider, repository_user, repository_name, email",
    [
        (
            RepositoryDeletionOrder.Status.PENDING,
            RepositoryDeletionOrder.Status.TRANSFERRING,
            RepositoryDeletionOrder.Provider.GITHUB,
            "user1",
            "repo1",
            "user1@example.com",
        ),
        (
            None,
            RepositoryDeletionOrder.Status.TRANSFERRING,
            RepositoryDeletionOrder.Provider.GITHUB,
            "user2",
            "repo2",
            "user2@example.com",
        ),
    ],
)
def test_repository_deletion_order_status_updated(
    mock_send_email_message,
    database: capy.Database,
    format: capy.Format,
    signals: capy.Signals,
    from_status: str,
    to_status: str,
    provider: str,
    repository_user: str,
    repository_name: str,
    email: str,
):
    signals.enable("breathecode.assignments.signals.status_updated")

    # Create the necessary database entries
    credentials = database.create(credentials_github={"username": repository_user}, user={"email": email})
    model = database.create(
        repository_deletion_order={
            "status": from_status or to_status,
            "provider": provider,
            "repository_user": repository_user,
            "repository_name": repository_name,
        }
    )

    if model.repository_deletion_order.status != to_status:
        model.repository_deletion_order.status = to_status
        model.repository_deletion_order.save()

    # Verify the email was sent
    assert database.list_of("authenticate.CredentialsGithub") == [
        format.to_obj_repr(credentials.credentials_github),
    ]

    assert database.list_of("assignments.RepositoryDeletionOrder") == [
        format.to_obj_repr(model.repository_deletion_order),
    ]

    # Check if send_email_message was called with the correct arguments
    mock_send_email_message.assert_called_once_with(
        "message",
        email,
        {
            "SUBJECT": f"We are transfering the repository {repository_name} to you",
            "MESSAGE": f"We are transfering the repository {repository_name} to you, you have "
            "two months to accept the transfer before we delete it",
            "BUTTON": "Go to the repository",
            "LINK": f"https://github.com/{repository_user}/{repository_name}",
        },
    )


@pytest.mark.parametrize(
    "from_status, to_status, provider, repository_user, repository_name, email",
    [
        (
            None,
            RepositoryDeletionOrder.Status.PENDING,
            RepositoryDeletionOrder.Provider.GITHUB,
            "user1",
            "repo1",
            "user1@example.com",
        ),
        (
            RepositoryDeletionOrder.Status.NO_STARTED,
            RepositoryDeletionOrder.Status.PENDING,
            RepositoryDeletionOrder.Provider.GITHUB,
            "user1",
            "repo1",
            "user1@example.com",
        ),
        (
            RepositoryDeletionOrder.Status.PENDING,
            RepositoryDeletionOrder.Status.ERROR,
            RepositoryDeletionOrder.Provider.GITHUB,
            "user2",
            "repo2",
            "user2@example.com",
        ),
        (
            RepositoryDeletionOrder.Status.PENDING,
            RepositoryDeletionOrder.Status.DELETED,
            RepositoryDeletionOrder.Provider.GITHUB,
            "user3",
            "repo3",
            "user3@example.com",
        ),
        (
            RepositoryDeletionOrder.Status.PENDING,
            RepositoryDeletionOrder.Status.CANCELLED,
            RepositoryDeletionOrder.Provider.GITHUB,
            "user3",
            "repo3",
            "user3@example.com",
        ),
        (
            RepositoryDeletionOrder.Status.PENDING,
            RepositoryDeletionOrder.Status.TRANSFERRED,
            RepositoryDeletionOrder.Provider.GITHUB,
            "user3",
            "repo3",
            "user3@example.com",
        ),
        *[
            (
                None,
                status,
                RepositoryDeletionOrder.Provider.GITHUB,
                "userx",
                "repox",
                "userx@example.com",
            )
            for status, _ in RepositoryDeletionOrder.Status.choices
            if status != RepositoryDeletionOrder.Status.TRANSFERRING
        ],
    ],
)
def test_repository_deletion_order_status_not_met(
    mock_send_email_message,
    database: capy.Database,
    format: capy.Format,
    signals: capy.Signals,
    from_status: str,
    to_status: str,
    provider: str,
    repository_user: str,
    repository_name: str,
    email: str,
):
    signals.enable("breathecode.assignments.signals.status_updated")
    # TRANSFERRING
    # Create the necessary database entries
    credentials = database.create(credentials_github={"username": repository_user}, user={"email": email})
    model = database.create(
        repository_deletion_order={
            "status": from_status or to_status,
            "provider": provider,
            "repository_user": repository_user,
            "repository_name": repository_name,
        }
    )

    if model.repository_deletion_order.status != to_status:
        model.repository_deletion_order.status = to_status
        model.repository_deletion_order.save()

    # # Trigger the signal
    # repository_deletion_order_status_updated(
    #     sender=RepositoryDeletionOrder,
    #     instance=repository_deletion_order.repository_deletion_order,
    # )

    # Verify the email was not sent
    assert database.list_of("authenticate.CredentialsGithub") == [
        format.to_obj_repr(credentials.credentials_github),
    ]

    assert database.list_of("assignments.RepositoryDeletionOrder") == [
        format.to_obj_repr(model.repository_deletion_order),
    ]

    # Check if send_email_message was not called
    mock_send_email_message.assert_not_called()
