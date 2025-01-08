"""
Test /answer
"""

from logging import Logger
from unittest.mock import MagicMock, call

import capyc.pytest as capy
import pytest
from linked_services.django.actions import reset_app_cache

from breathecode.notify import actions

from ...tasks import send_repository_deletion_notification


@pytest.fixture(autouse=True)
def x(db, monkeypatch: pytest.MonkeyPatch):
    empty = lambda *args, **kwargs: None

    reset_app_cache()

    monkeypatch.setattr("logging.Logger.info", MagicMock())
    monkeypatch.setattr("logging.Logger.error", MagicMock())

    monkeypatch.setattr("breathecode.notify.actions.send_email_message", MagicMock())

    yield


def test_no_order(database: capy.Database):
    send_repository_deletion_notification.delay(1, "bob")

    assert Logger.info.call_args_list == [
        call("Executing send_repository_deletion_notification for cohort user 1"),
        call("Executing send_repository_deletion_notification for cohort user 1"),
    ]
    assert Logger.error.call_args_list == [
        call("Repository deletion order not found", exc_info=True),
    ]
    assert database.list_of("assignments.RepositoryDeletionOrder") == []
    assert actions.send_email_message.call_args_list == []


def test_not_found_user(database: capy.Database, format: capy.Format):
    model = database.create(repository_deletion_order={"status": "TRANSFERRING"})
    Logger.info.reset_mock()
    send_repository_deletion_notification.delay(1, "bob")

    assert Logger.info.call_args_list == [
        call("Executing send_repository_deletion_notification for cohort user 1"),
    ]
    assert Logger.error.call_args_list == [
        call("User not found for GITHUB username bob", exc_info=True),
    ]
    assert database.list_of("assignments.RepositoryDeletionOrder") == [
        format.to_obj_repr(model.repository_deletion_order)
    ]
    assert actions.send_email_message.call_args_list == []


def test_transferring(database: capy.Database, format: capy.Format, utc_now):
    model = database.create(
        repository_deletion_order={"status": "TRANSFERRING"}, user=1, credentials_github={"username": "bob"}
    )
    Logger.info.reset_mock()
    send_repository_deletion_notification.delay(1, "bob")

    assert Logger.info.call_args_list == [
        call("Executing send_repository_deletion_notification for cohort user 1"),
    ]
    assert Logger.error.call_args_list == []
    assert database.list_of("assignments.RepositoryDeletionOrder") == [
        {
            **format.to_obj_repr(model.repository_deletion_order),
            "notified_at": utc_now,
        }
    ]

    assert actions.send_email_message.call_args_list == [
        call(
            "message",
            model.user.email,
            {
                "SUBJECT": f"We are transfering the repository {model.repository_deletion_order.repository_name} to you",
                "MESSAGE": f"We are transfering the repository {model.repository_deletion_order.repository_name} to you, you have two months to accept the transfer before we delete it",
                "BUTTON": "Go to the repository",
                "LINK": f"https://github.com/{model.repository_deletion_order.repository_user}/{model.repository_deletion_order.repository_name}",
            },
        )
    ]
