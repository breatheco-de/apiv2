"""
Test /answer
"""

from typing import Any
from unittest.mock import MagicMock, call

import capyc.pytest as capyc
import pytest
from dateutil.relativedelta import relativedelta
from linked_services.django.actions import reset_app_cache

from breathecode.assignments import tasks
from breathecode.assignments.management.commands.send_deletion_order_notifications import Command
from breathecode.registry.models import Asset


@pytest.fixture(autouse=True)
def setup(db, monkeypatch: pytest.MonkeyPatch):
    reset_app_cache()
    monkeypatch.setattr("breathecode.assignments.tasks.send_repository_deletion_notification.delay", MagicMock())
    yield


# https://api.github.com/repos/{org}/{repo}/events
class Event:

    @staticmethod
    def push(login: str) -> dict[str, Any]:
        return {
            "type": "PushEvent",
            "actor": {
                "login": login,
            },
        }

    @staticmethod
    def member(login: str, action: str = "added") -> dict[str, Any]:
        return {
            "type": "MemberEvent",
            "payload": {
                "member": {
                    "login": login,
                },
                "action": action,
            },
        }

    @staticmethod
    def watch(login: str) -> dict[str, Any]:
        return {
            "type": "WatchEvent",
            "actor": {
                "login": login,
            },
        }


class ResponseMock:

    def __init__(self, data, status=200, headers={}):
        self.content = data
        self.status_code = status
        self.headers = headers

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    def json(self):
        return self.content


@pytest.fixture
def patch_get(monkeypatch):

    def handler(objs):

        def x(*args, **kwargs):
            nonlocal objs
            res = [obj for obj in objs if obj["url"] == kwargs["url"] and obj["method"] == kwargs["method"]]

            if len(res) == 0:
                return ResponseMock({}, 404, {})
            return ResponseMock(res[0]["expected"], res[0]["code"], res[0]["headers"])

        monkeypatch.setattr("requests.request", MagicMock(side_effect=x))

    yield handler


def test_no_settings(database: capyc.Database):
    command = Command()
    command.handle()

    assert database.list_of("assignments.RepositoryDeletionOrder") == []
    assert database.list_of("assignments.RepositoryWhiteList") == []
    assert tasks.send_repository_deletion_notification.delay.call_args_list == []


@pytest.mark.parametrize(
    "event",
    [
        Event.push("breatheco-de"),
        Event.member("breatheco-de"),
        Event.watch("breatheco-de"),
    ],
)
def test_one_repo__pending__user_found(
    database: capyc.Database, format: capyc.Format, patch_get, set_datetime, utc_now, event
):

    delta = relativedelta(months=2, hours=1)
    github_username = "breatheco-de"
    parsed_name = github_username.replace("-", "")
    model = database.create(
        academy_auth_settings={"github_username": github_username},
        city=1,
        country=1,
        user=1,
        credentials_github=1,
        repository_deletion_order=[
            {
                "provider": "GITHUB",
                "repository_name": f"curso-nodejs-4geeks-{parsed_name}",
                "repository_user": github_username,
                "status": "PENDING",
                "status_text": None,
            },
        ],
    )
    set_datetime(utc_now - delta)

    patch_get(
        [
            {
                "method": "GET",
                "url": f"https://api.github.com/orgs/{model.academy_auth_settings.github_username}/curso-nodejs-4geeks-{parsed_name}/events?page=1&per_page=30",
                "expected": [event],
                "code": 200,
                "headers": {},
            },
        ]
    )
    command = Command()
    command.handle()

    assert database.list_of("assignments.RepositoryDeletionOrder") == [
        format.to_obj_repr(model.repository_deletion_order),
    ]
    assert database.list_of("assignments.RepositoryWhiteList") == []
    assert tasks.send_repository_deletion_notification.delay.call_args_list == [
        call(1, "breatheco-de"),
    ]


def test_one_repo__pending__user_found__inferred(
    database: capyc.Database, format: capyc.Format, patch_get, set_datetime, utc_now
):
    event = Event.member("4GeeksAcademy")

    delta = relativedelta(months=2, hours=1)
    github_username = "4GeeksAcademy"
    model = database.create(
        academy_auth_settings={"github_username": github_username},
        city=1,
        country=1,
        user=1,
        credentials_github=1,
        repository_deletion_order=[
            {
                "provider": "GITHUB",
                "repository_name": "curso-nodejs-4geeks",
                "repository_user": github_username,
                "status": "PENDING",
                "status_text": None,
            },
        ],
    )
    set_datetime(utc_now - delta)

    patch_get(
        [
            {
                "method": "GET",
                "url": f"https://api.github.com/orgs/{model.academy_auth_settings.github_username}/curso-nodejs-4geeks/events?page=1&per_page=30",
                "expected": [event],
                "code": 200,
                "headers": {},
            },
        ]
    )
    command = Command()
    command.handle()

    assert database.list_of("assignments.RepositoryDeletionOrder") == [
        format.to_obj_repr(model.repository_deletion_order),
    ]
    assert database.list_of("assignments.RepositoryWhiteList") == []
    assert tasks.send_repository_deletion_notification.delay.call_args_list == [
        call(1, "4GeeksAcademy"),
    ]
