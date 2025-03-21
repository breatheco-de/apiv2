"""
Test /answer
"""

import re
from datetime import datetime
from typing import Any, Optional
from unittest.mock import MagicMock, call

import capyc.pytest as capyc
import pytest
import requests
from dateutil.relativedelta import relativedelta
from linked_services.django.actions import reset_app_cache

from breathecode.assignments import tasks
from breathecode.assignments.management.commands.schedule_repository_deletions import Command
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


def test_no_repos(database: capyc.Database, patch_get):
    model = database.create(academy_auth_settings=1, city=1, country=1, user=1, credentials_github=1)
    patch_get(
        [
            {
                "method": "GET",
                "url": f"https://api.github.com/orgs/{model.academy_auth_settings.github_username}/repos?page=1&type=forks&per_page=30&sort=created&direction=desc",
                "expected": [],
                "code": 200,
                "headers": {},
            },
        ]
    )
    command = Command()
    command.handle()

    assert database.list_of("assignments.RepositoryDeletionOrder") == []
    assert database.list_of("assignments.RepositoryWhiteList") == []
    assert tasks.send_repository_deletion_notification.delay.call_args_list == []


def test_two_repos(database: capyc.Database, patch_get):
    model = database.create(academy_auth_settings=1, city=1, country=1, user=1, credentials_github=1)
    patch_get(
        [
            {
                "method": "GET",
                "url": f"https://api.github.com/orgs/{model.academy_auth_settings.github_username}/repos?page=1&type=forks&per_page=30&sort=created&direction=desc",
                "expected": [
                    {
                        "private": False,
                        "html_url": "https://github.com/breatheco-de/curso-nodejs-4geeks",
                        "fork": True,
                        "created_at": "2024-04-05T19:22:39Z",
                        "is_template": False,
                        "allow_forking": True,
                    },
                    {
                        "private": False,
                        "html_url": "https://github.com/4GeeksAcademy/curso-nodejs-4geeks",
                        "fork": True,
                        "created_at": "2024-04-05T19:22:39Z",
                        "is_template": False,
                        "allow_forking": True,
                    },
                ],
                "code": 200,
                "headers": {},
            },
        ]
    )
    command = Command()
    command.handle()

    assert database.list_of("assignments.RepositoryDeletionOrder") == [
        {
            "id": 1,
            "provider": "GITHUB",
            "repository_name": "curso-nodejs-4geeks",
            "repository_user": "breatheco-de",
            "status": "PENDING",
            "status_text": None,
            "starts_transferring_at": None,
            "notified_at": None,
            "user_id": None,
        },
        {
            "id": 2,
            "provider": "GITHUB",
            "repository_name": "curso-nodejs-4geeks",
            "repository_user": "4GeeksAcademy",
            "status": "PENDING",
            "status_text": None,
            "starts_transferring_at": None,
            "notified_at": None,
            "user_id": None,
        },
    ]
    assert database.list_of("assignments.RepositoryWhiteList") == []
    assert tasks.send_repository_deletion_notification.delay.call_args_list == []


def test_two_repos__deleting_repositories(database: capyc.Database, patch_get, set_datetime, utc_now):

    delta = relativedelta(months=2, hours=1)
    model = database.create(
        academy_auth_settings=1,
        city=1,
        country=1,
        user=1,
        credentials_github=1,
        repository_deletion_order=[
            {
                "provider": "GITHUB",
                "repository_name": "curso-nodejs-4geeks",
                "repository_user": "breatheco-de",
                "status": "PENDING",
                "status_text": None,
            },
            {
                "provider": "GITHUB",
                "repository_name": "curso-nodejs-4geeks",
                "repository_user": "4GeeksAcademy",
                "status": "PENDING",
                "status_text": None,
            },
        ],
    )
    set_datetime(utc_now + delta)

    patch_get(
        [
            {
                "method": "GET",
                "url": f"https://api.github.com/orgs/{model.academy_auth_settings.github_username}/repos?page=1&type=forks&per_page=30&sort=created&direction=desc",
                "expected": [
                    {
                        "private": False,
                        "html_url": "https://github.com/breatheco-de/curso-nodejs-4geeks",
                        "fork": True,
                        "created_at": "2024-04-05T19:22:39Z",
                        "is_template": False,
                        "allow_forking": True,
                    },
                    {
                        "private": False,
                        "html_url": "https://github.com/4GeeksAcademy/curso-nodejs-4geeks",
                        "fork": True,
                        "created_at": "2024-04-05T19:22:39Z",
                        "is_template": False,
                        "allow_forking": True,
                    },
                ],
                "code": 200,
                "headers": {},
            },
            {
                "method": "DELETE",
                "url": "https://api.github.com/repos/breatheco-de/curso-nodejs-4geeks",
                "expected": None,
                "code": 204,
                "headers": {},
            },
            {
                "method": "DELETE",
                "url": "https://api.github.com/repos/4GeeksAcademy/curso-nodejs-4geeks",
                "expected": None,
                "code": 204,
                "headers": {},
            },
            {
                "method": "HEAD",
                "url": "https://api.github.com/repos/breatheco-de/curso-nodejs-4geeks",
                "expected": None,
                "code": 200,
                "headers": {},
            },
            {
                "method": "HEAD",
                "url": "https://api.github.com/repos/4GeeksAcademy/curso-nodejs-4geeks",
                "expected": None,
                "code": 200,
                "headers": {},
            },
        ]
    )
    command = Command()
    command.handle()

    assert database.list_of("assignments.RepositoryDeletionOrder") == [
        {
            "id": 1,
            "provider": "GITHUB",
            "repository_name": "curso-nodejs-4geeks",
            "repository_user": "breatheco-de",
            "status": "DELETED",
            "status_text": None,
            "starts_transferring_at": None,
            "notified_at": None,
            "user_id": 1,
        },
        {
            "id": 2,
            "provider": "GITHUB",
            "repository_name": "curso-nodejs-4geeks",
            "repository_user": "4GeeksAcademy",
            "status": "DELETED",
            "status_text": None,
            "starts_transferring_at": None,
            "notified_at": None,
            "user_id": 1,
        },
    ]
    assert database.list_of("assignments.RepositoryWhiteList") == []
    assert tasks.send_repository_deletion_notification.delay.call_args_list == []


def test_two_repos__repository_transferred(database: capyc.Database, patch_get, set_datetime, utc_now):

    delta = relativedelta(months=2, hours=1)
    model = database.create(
        academy_auth_settings=1,
        city=1,
        country=1,
        user=1,
        credentials_github=1,
        repository_deletion_order=[
            {
                "provider": "GITHUB",
                "repository_name": "curso-nodejs-4geeks",
                "repository_user": "breatheco-de",
                "status": "TRANSFERRING",
                "status_text": None,
            },
            {
                "provider": "GITHUB",
                "repository_name": "curso-nodejs-4geeks",
                "repository_user": "4GeeksAcademy",
                "status": "TRANSFERRING",
                "status_text": None,
            },
        ],
    )
    set_datetime(utc_now + delta)

    patch_get(
        [
            {
                "method": "GET",
                "url": f"https://api.github.com/orgs/{model.academy_auth_settings.github_username}/repos?page=1&type=forks&per_page=30&sort=created&direction=desc",
                "expected": [
                    {
                        "private": False,
                        "html_url": "https://github.com/breatheco-de/curso-nodejs-4geeks",
                        "fork": True,
                        "created_at": "2024-04-05T19:22:39Z",
                        "is_template": False,
                        "allow_forking": True,
                    },
                    {
                        "private": False,
                        "html_url": "https://github.com/4GeeksAcademy/curso-nodejs-4geeks",
                        "fork": True,
                        "created_at": "2024-04-05T19:22:39Z",
                        "is_template": False,
                        "allow_forking": True,
                    },
                ],
                "code": 200,
                "headers": {},
            },
        ]
    )
    command = Command()
    command.handle()

    assert database.list_of("assignments.RepositoryDeletionOrder") == [
        {
            "id": 1,
            "provider": "GITHUB",
            "repository_name": "curso-nodejs-4geeks",
            "repository_user": "breatheco-de",
            "status": "TRANSFERRED",
            "status_text": None,
            "starts_transferring_at": utc_now,
            "notified_at": None,
            "user_id": 1,
        },
        {
            "id": 2,
            "provider": "GITHUB",
            "repository_name": "curso-nodejs-4geeks",
            "repository_user": "4GeeksAcademy",
            "status": "TRANSFERRED",
            "status_text": None,
            "starts_transferring_at": utc_now,
            "notified_at": None,
            "user_id": 1,
        },
    ]
    assert database.list_of("assignments.RepositoryWhiteList") == []
    assert tasks.send_repository_deletion_notification.delay.call_args_list == []


def test_two_repos__repository_does_not_exists(database: capyc.Database, patch_get, set_datetime, utc_now):

    delta = relativedelta(months=2, hours=1)
    model = database.create(
        academy_auth_settings=1,
        city=1,
        country=1,
        user=1,
        credentials_github=1,
        repository_deletion_order=[
            {
                "provider": "GITHUB",
                "repository_name": "curso-nodejs-4geeks",
                "repository_user": "breatheco-de",
                "status": "PENDING",
                "status_text": None,
            },
            {
                "provider": "GITHUB",
                "repository_name": "curso-nodejs-4geeks",
                "repository_user": "4GeeksAcademy",
                "status": "PENDING",
                "status_text": None,
            },
        ],
    )
    set_datetime(utc_now + delta)

    patch_get(
        [
            {
                "method": "GET",
                "url": f"https://api.github.com/orgs/{model.academy_auth_settings.github_username}/repos?page=1&type=forks&per_page=30&sort=created&direction=desc",
                "expected": [
                    {
                        "private": False,
                        "html_url": "https://github.com/breatheco-de/curso-nodejs-4geeks",
                        "fork": True,
                        "created_at": "2024-04-05T19:22:39Z",
                        "is_template": False,
                        "allow_forking": True,
                    },
                    {
                        "private": False,
                        "html_url": "https://github.com/4GeeksAcademy/curso-nodejs-4geeks",
                        "fork": True,
                        "created_at": "2024-04-05T19:22:39Z",
                        "is_template": False,
                        "allow_forking": True,
                    },
                ],
                "code": 200,
                "headers": {},
            },
        ]
    )
    command = Command()
    command.handle()

    assert database.list_of("assignments.RepositoryDeletionOrder") == [
        {
            "id": 1,
            "provider": "GITHUB",
            "repository_name": "curso-nodejs-4geeks",
            "repository_user": "breatheco-de",
            "status": "ERROR",
            "status_text": "Repository does not exist: breatheco-de/curso-nodejs-4geeks",
            "starts_transferring_at": None,
            "notified_at": None,
            "user_id": 1,
        },
        {
            "id": 2,
            "provider": "GITHUB",
            "repository_name": "curso-nodejs-4geeks",
            "repository_user": "4GeeksAcademy",
            "status": "ERROR",
            "status_text": "Repository does not exist: 4GeeksAcademy/curso-nodejs-4geeks",
            "starts_transferring_at": None,
            "notified_at": None,
            "user_id": 1,
        },
    ]
    assert database.list_of("assignments.RepositoryWhiteList") == []
    assert tasks.send_repository_deletion_notification.delay.call_args_list == []


def test_one_repo__pending__user_not_found(database: capyc.Database, patch_get, set_datetime, utc_now, fake):

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
                "url": f"https://api.github.com/orgs/{model.academy_auth_settings.github_username}/repos?page=1&type=forks&per_page=30&sort=created&direction=desc",
                "expected": [
                    {
                        "private": False,
                        "html_url": f"https://github.com/{model.academy_auth_settings.github_username}/curso-nodejs-4geeks",
                        "fork": True,
                        "created_at": "2024-04-05T19:22:39Z",
                        "is_template": False,
                        "allow_forking": True,
                    },
                ],
                "code": 200,
                "headers": {},
            },
            {
                "method": "GET",
                "url": f"https://api.github.com/repos/{model.academy_auth_settings.github_username}/curso-nodejs-4geeks/events?page=1&per_page=30",
                "expected": [],
                "code": 200,
                "headers": {},
            },
        ]
    )
    command = Command()
    command.handle()

    assert database.list_of("assignments.RepositoryDeletionOrder") == [
        {
            "id": 1,
            "provider": "GITHUB",
            "repository_name": "curso-nodejs-4geeks",
            "repository_user": github_username,
            "status": "PENDING",
            "status_text": None,
            "starts_transferring_at": None,
            "notified_at": None,
            "user_id": 1,
        },
    ]
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
                "url": f"https://api.github.com/orgs/{model.academy_auth_settings.github_username}/repos?page=1&type=forks&per_page=30&sort=created&direction=desc",
                "expected": [
                    {
                        "private": False,
                        "html_url": f"https://github.com/{model.academy_auth_settings.github_username}/curso-nodejs-4geeks-{parsed_name}",
                        "fork": True,
                        "created_at": "2024-04-05T19:22:39Z",
                        "is_template": False,
                        "allow_forking": True,
                    },
                ],
                "code": 200,
                "headers": {},
            },
            {
                "method": "HEAD",
                "url": f"https://api.github.com/repos/{model.academy_auth_settings.github_username}/curso-nodejs-4geeks-{parsed_name}",
                "expected": None,
                "code": 200,
                "headers": {},
            },
            {
                "method": "POST",
                "url": f"https://api.github.com/repos/{model.academy_auth_settings.github_username}/curso-nodejs-4geeks-{parsed_name}/transfer",
                "expected": {},
                "code": 202,
                "headers": {},
            },
            {
                "method": "GET",
                "url": f"https://api.github.com/repos/{model.academy_auth_settings.github_username}/curso-nodejs-4geeks-{parsed_name}/events?page=1&per_page=30",
                "expected": [event],
                "code": 200,
                "headers": {},
            },
        ]
    )
    command = Command()
    command.handle()

    assert database.list_of("assignments.RepositoryDeletionOrder") == [
        {
            **format.to_obj_repr(model.repository_deletion_order),
            "status": "TRANSFERRING",
            "starts_transferring_at": utc_now - delta,
            "notified_at": None,
        }
    ]
    assert database.list_of("assignments.RepositoryWhiteList") == []
    assert tasks.send_repository_deletion_notification.delay.call_args_list == [
        call(1, "breatheco-de"),
    ]


def test_one_repo__pending__user_found__inferred(database: capyc.Database, patch_get, set_datetime, utc_now):
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
                "url": f"https://api.github.com/orgs/{model.academy_auth_settings.github_username}/repos?page=1&type=forks&per_page=30&sort=created&direction=desc",
                "expected": [
                    {
                        "private": False,
                        "html_url": f"https://github.com/{model.academy_auth_settings.github_username}/curso-nodejs-4geeks",
                        "fork": True,
                        "created_at": "2024-04-05T19:22:39Z",
                        "is_template": False,
                        "allow_forking": True,
                    },
                ],
                "code": 200,
                "headers": {},
            },
            {
                "method": "HEAD",
                "url": f"https://api.github.com/repos/{model.academy_auth_settings.github_username}/curso-nodejs-4geeks",
                "expected": None,
                "code": 200,
                "headers": {},
            },
            {
                "method": "POST",
                "url": f"https://api.github.com/repos/{model.academy_auth_settings.github_username}/curso-nodejs-4geeks/transfer",
                "expected": {},
                "code": 202,
                "headers": {},
            },
            {
                "method": "GET",
                "url": f"https://api.github.com/repos/{model.academy_auth_settings.github_username}/curso-nodejs-4geeks/events?page=1&per_page=30",
                "expected": [event],
                "code": 200,
                "headers": {},
            },
        ]
    )
    command = Command()
    command.handle()

    assert database.list_of("assignments.RepositoryDeletionOrder") == [
        {
            "id": 1,
            "provider": "GITHUB",
            "repository_name": f"curso-nodejs-4geeks",
            "repository_user": github_username,
            "status": "TRANSFERRING",
            "status_text": None,
            "starts_transferring_at": utc_now - delta,
            "notified_at": None,
            "user_id": 1,
        },
    ]
    assert database.list_of("assignments.RepositoryWhiteList") == []
    assert tasks.send_repository_deletion_notification.delay.call_args_list == [
        call(1, "4GeeksAcademy"),
    ]


def test_one_repo__transferring__repo_found(database: capyc.Database, patch_get, set_datetime, utc_now):
    delta = relativedelta(months=2, hours=1)
    github_username = "breatheco-de"
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
                "status": "TRANSFERRING",
                "status_text": None,
            },
        ],
    )
    set_datetime(utc_now - delta)

    patch_get(
        [
            {
                "method": "GET",
                "url": f"https://api.github.com/orgs/{model.academy_auth_settings.github_username}/repos?page=1&type=forks&per_page=30&sort=created&direction=desc",
                "expected": [
                    {
                        "private": False,
                        "html_url": f"https://github.com/{model.academy_auth_settings.github_username}/curso-nodejs-4geeks",
                        "fork": True,
                        "created_at": "2024-04-05T19:22:39Z",
                        "is_template": False,
                        "allow_forking": True,
                    },
                ],
                "code": 200,
                "headers": {},
            },
            {
                "method": "HEAD",
                "url": f"https://api.github.com/repos/{model.academy_auth_settings.github_username}/curso-nodejs-4geeks",
                "expected": None,
                "code": 200,
                "headers": {},
            },
        ]
    )
    command = Command()
    command.handle()

    assert database.list_of("assignments.RepositoryDeletionOrder") == [
        {
            "id": 1,
            "provider": "GITHUB",
            "repository_name": "curso-nodejs-4geeks",
            "repository_user": github_username,
            "status": "TRANSFERRING",
            "status_text": None,
            "starts_transferring_at": utc_now,
            "notified_at": None,
            "user_id": 1,
        },
    ]
    assert database.list_of("assignments.RepositoryWhiteList") == []
    assert tasks.send_repository_deletion_notification.delay.call_args_list == []


def test_one_repo__transferring__repo_not_found(database: capyc.Database, patch_get, set_datetime, utc_now):
    delta = relativedelta(months=2, hours=1)
    github_username = "breatheco-de"
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
                "status": "TRANSFERRING",
                "status_text": None,
            },
        ],
    )
    set_datetime(utc_now - delta)

    patch_get(
        [
            {
                "method": "GET",
                "url": f"https://api.github.com/orgs/{model.academy_auth_settings.github_username}/repos?page=1&type=forks&per_page=30&sort=created&direction=desc",
                "expected": [
                    {
                        "private": False,
                        "html_url": f"https://github.com/{model.academy_auth_settings.github_username}/curso-nodejs-4geeks",
                        "fork": True,
                        "created_at": "2024-04-05T19:22:39Z",
                        "is_template": False,
                        "allow_forking": True,
                    },
                ],
                "code": 200,
                "headers": {},
            },
            {
                "method": "HEAD",
                "url": f"https://api.github.com/repos/{model.academy_auth_settings.github_username}/curso-nodejs-4geeks",
                "expected": None,
                "code": 404,
                "headers": {},
            },
        ]
    )
    command = Command()
    command.handle()

    assert database.list_of("assignments.RepositoryDeletionOrder") == [
        {
            "id": 1,
            "provider": "GITHUB",
            "repository_name": "curso-nodejs-4geeks",
            "repository_user": github_username,
            "status": "TRANSFERRED",
            "status_text": None,
            "starts_transferring_at": utc_now,
            "notified_at": None,
            "user_id": 1,
        },
    ]
    assert database.list_of("assignments.RepositoryWhiteList") == []
    assert tasks.send_repository_deletion_notification.delay.call_args_list == []


def test_two_repos_in_the_whitelist(database: capyc.Database, patch_get):
    model = database.create(
        academy_auth_settings=1,
        city=1,
        country=1,
        user=1,
        credentials_github=1,
        repository_white_list=[
            {
                "provider": "GITHUB",
                "repository_name": "curso-nodejs-4geeks",
                "repository_user": "breatheco-de",
            },
            {
                "provider": "GITHUB",
                "repository_name": "curso-nodejs-4geeks",
                "repository_user": "4GeeksAcademy",
            },
        ],
    )
    patch_get(
        [
            {
                "method": "GET",
                "url": f"https://api.github.com/orgs/{model.academy_auth_settings.github_username}/repos?page=1&type=forks&per_page=30&sort=created&direction=desc",
                "expected": [
                    {
                        "private": False,
                        "html_url": "https://github.com/breatheco-de/curso-nodejs-4geeks",
                        "fork": True,
                        "created_at": "2024-04-05T19:22:39Z",
                        "is_template": False,
                        "allow_forking": True,
                    },
                    {
                        "private": False,
                        "html_url": "https://github.com/4GeeksAcademy/curso-nodejs-4geeks",
                        "fork": True,
                        "created_at": "2024-04-05T19:22:39Z",
                        "is_template": False,
                        "allow_forking": True,
                    },
                ],
                "code": 200,
                "headers": {},
            },
        ]
    )
    command = Command()
    command.handle()

    assert database.list_of("assignments.RepositoryDeletionOrder") == []
    assert database.list_of("assignments.RepositoryWhiteList") == [
        {
            "id": 1,
            "provider": "GITHUB",
            "repository_name": "curso-nodejs-4geeks",
            "repository_user": "breatheco-de",
        },
        {
            "id": 2,
            "provider": "GITHUB",
            "repository_name": "curso-nodejs-4geeks",
            "repository_user": "4GeeksAcademy",
        },
    ]
    assert tasks.send_repository_deletion_notification.delay.call_args_list == []


def test_two_repos_scheduled_and_in_this_execution_was_added_to_the_whitelist(database: capyc.Database, patch_get):
    model = database.create(
        academy_auth_settings=1,
        city=1,
        country=1,
        user=1,
        credentials_github=1,
        repository_white_list=[
            {
                "provider": "GITHUB",
                "repository_name": "curso-nodejs-4geeks",
                "repository_user": "breatheco-de",
            },
            {
                "provider": "GITHUB",
                "repository_name": "curso-nodejs-4geeks",
                "repository_user": "4GeeksAcademy",
            },
        ],
        repository_deletion_order=[
            {
                "provider": "GITHUB",
                "repository_name": "curso-nodejs-4geeks",
                "repository_user": "breatheco-de",
                "status": "PENDING",
                "status_text": None,
            },
            {
                "provider": "GITHUB",
                "repository_name": "curso-nodejs-4geeks",
                "repository_user": "4GeeksAcademy",
                "status": "PENDING",
                "status_text": None,
            },
        ],
    )
    patch_get(
        [
            {
                "method": "GET",
                "url": f"https://api.github.com/orgs/{model.academy_auth_settings.github_username}/repos?page=1&type=forks&per_page=30&sort=created&direction=desc",
                "expected": [
                    {
                        "private": False,
                        "html_url": "https://github.com/breatheco-de/curso-nodejs-4geeks",
                        "fork": True,
                        "created_at": "2024-04-05T19:22:39Z",
                        "is_template": False,
                        "allow_forking": True,
                    },
                    {
                        "private": False,
                        "html_url": "https://github.com/4GeeksAcademy/curso-nodejs-4geeks",
                        "fork": True,
                        "created_at": "2024-04-05T19:22:39Z",
                        "is_template": False,
                        "allow_forking": True,
                    },
                ],
                "code": 200,
                "headers": {},
            },
        ]
    )
    command = Command()
    command.handle()

    assert database.list_of("assignments.RepositoryDeletionOrder") == []
    assert database.list_of("assignments.RepositoryWhiteList") == [
        {
            "id": 1,
            "provider": "GITHUB",
            "repository_name": "curso-nodejs-4geeks",
            "repository_user": "breatheco-de",
        },
        {
            "id": 2,
            "provider": "GITHUB",
            "repository_name": "curso-nodejs-4geeks",
            "repository_user": "4GeeksAcademy",
        },
    ]
    assert tasks.send_repository_deletion_notification.delay.call_args_list == []


def test_two_repos_used_in_subscriptions(database: capyc.Database, patch_get):
    model = database.create(
        academy_auth_settings=1,
        city=1,
        country=1,
        user=1,
        credentials_github=1,
        repository_subscription=[
            {
                "repository": "https://github.com/breatheco-de/curso-nodejs-4geeks",
            },
            {
                "repository": "https://github.com/4GeeksAcademy/curso-nodejs-4geeks",
            },
        ],
    )
    patch_get(
        [
            {
                "method": "GET",
                "url": f"https://api.github.com/orgs/{model.academy_auth_settings.github_username}/repos?page=1&type=forks&per_page=30&sort=created&direction=desc",
                "expected": [
                    {
                        "private": False,
                        "html_url": "https://github.com/breatheco-de/curso-nodejs-4geeks",
                        "fork": True,
                        "created_at": "2024-04-05T19:22:39Z",
                        "is_template": False,
                        "allow_forking": True,
                    },
                    {
                        "private": False,
                        "html_url": "https://github.com/4GeeksAcademy/curso-nodejs-4geeks",
                        "fork": True,
                        "created_at": "2024-04-05T19:22:39Z",
                        "is_template": False,
                        "allow_forking": True,
                    },
                ],
                "code": 200,
                "headers": {},
            },
        ]
    )
    command = Command()
    command.handle()

    assert database.list_of("assignments.RepositoryDeletionOrder") == []
    assert database.list_of("assignments.RepositoryWhiteList") == [
        {
            "id": 1,
            "provider": "GITHUB",
            "repository_name": "curso-nodejs-4geeks",
            "repository_user": "breatheco-de",
        },
        {
            "id": 2,
            "provider": "GITHUB",
            "repository_name": "curso-nodejs-4geeks",
            "repository_user": "4GeeksAcademy",
        },
    ]
    assert tasks.send_repository_deletion_notification.delay.call_args_list == []


def test_two_repos_scheduled_and_in_this_execution_was_added_to_the_subscriptions(database: capyc.Database, patch_get):
    model = database.create(
        academy_auth_settings=1,
        city=1,
        country=1,
        user=1,
        credentials_github=1,
        repository_subscription=[
            {
                "repository": "https://github.com/breatheco-de/curso-nodejs-4geeks",
            },
            {
                "repository": "https://github.com/4GeeksAcademy/curso-nodejs-4geeks",
            },
        ],
        repository_deletion_order=[
            {
                "provider": "GITHUB",
                "repository_name": "curso-nodejs-4geeks",
                "repository_user": "breatheco-de",
                "status": "PENDING",
                "status_text": None,
            },
            {
                "provider": "GITHUB",
                "repository_name": "curso-nodejs-4geeks",
                "repository_user": "4GeeksAcademy",
                "status": "PENDING",
                "status_text": None,
            },
        ],
    )
    patch_get(
        [
            {
                "method": "GET",
                "url": f"https://api.github.com/orgs/{model.academy_auth_settings.github_username}/repos?page=1&type=forks&per_page=30&sort=created&direction=desc",
                "expected": [
                    {
                        "private": False,
                        "html_url": "https://github.com/breatheco-de/curso-nodejs-4geeks",
                        "fork": True,
                        "created_at": "2024-04-05T19:22:39Z",
                        "is_template": False,
                        "allow_forking": True,
                    },
                    {
                        "private": False,
                        "html_url": "https://github.com/4GeeksAcademy/curso-nodejs-4geeks",
                        "fork": True,
                        "created_at": "2024-04-05T19:22:39Z",
                        "is_template": False,
                        "allow_forking": True,
                    },
                ],
                "code": 200,
                "headers": {},
            },
        ]
    )
    command = Command()
    command.handle()

    assert database.list_of("assignments.RepositoryDeletionOrder") == []
    assert database.list_of("assignments.RepositoryWhiteList") == [
        {
            "id": 1,
            "provider": "GITHUB",
            "repository_name": "curso-nodejs-4geeks",
            "repository_user": "breatheco-de",
        },
        {
            "id": 2,
            "provider": "GITHUB",
            "repository_name": "curso-nodejs-4geeks",
            "repository_user": "4GeeksAcademy",
        },
    ]
    assert tasks.send_repository_deletion_notification.delay.call_args_list == []


@pytest.mark.parametrize(
    "attr, is_readme, is_joined",
    [
        ("url", False, False),
        ("solution_url", False, False),
        ("preview", False, False),
        ("readme_url", False, False),
        ("intro_video_url", False, False),
        ("solution_video_url", False, False),
        ("readme_raw", True, False),
        ("readme_raw", True, True),
    ],
)
def test_two_repos_used_in_assets(database: capyc.Database, patch_get, attr, is_readme, is_joined):
    if is_readme and is_joined:
        assets = [
            {
                attr: Asset.encode(
                    "https://github.com/breatheco-de/curso-nodejs-4geeks https://github.com/4GeeksAcademy/curso-nodejs-4geeks"
                ),
            },
        ]
    elif is_readme and is_joined is False:
        assets = [
            {
                attr: Asset.encode("https://github.com/breatheco-de/curso-nodejs-4geeks"),
            },
            {
                attr: Asset.encode("https://github.com/4GeeksAcademy/curso-nodejs-4geeks"),
            },
        ]
    else:
        assets = [
            {
                attr: "https://github.com/breatheco-de/curso-nodejs-4geeks",
            },
            {
                attr: "https://github.com/4GeeksAcademy/curso-nodejs-4geeks",
            },
        ]
    model = database.create(
        academy_auth_settings=1, city=1, country=1, user=1, credentials_github=1, asset=assets, asset_category=1
    )
    patch_get(
        [
            {
                "method": "GET",
                "url": f"https://api.github.com/orgs/{model.academy_auth_settings.github_username}/repos?page=1&type=forks&per_page=30&sort=created&direction=desc",
                "expected": [
                    {
                        "private": False,
                        "html_url": "https://github.com/breatheco-de/curso-nodejs-4geeks",
                        "fork": True,
                        "created_at": "2024-04-05T19:22:39Z",
                        "is_template": False,
                        "allow_forking": True,
                    },
                    {
                        "private": False,
                        "html_url": "https://github.com/4GeeksAcademy/curso-nodejs-4geeks",
                        "fork": True,
                        "created_at": "2024-04-05T19:22:39Z",
                        "is_template": False,
                        "allow_forking": True,
                    },
                ],
                "code": 200,
                "headers": {},
            },
        ]
    )
    command = Command()
    command.handle()

    assert database.list_of("assignments.RepositoryDeletionOrder") == []
    assert database.list_of("assignments.RepositoryWhiteList") == [
        {
            "id": 1,
            "provider": "GITHUB",
            "repository_name": "curso-nodejs-4geeks",
            "repository_user": "breatheco-de",
        },
        {
            "id": 2,
            "provider": "GITHUB",
            "repository_name": "curso-nodejs-4geeks",
            "repository_user": "4GeeksAcademy",
        },
    ]
    assert tasks.send_repository_deletion_notification.delay.call_args_list == []


@pytest.mark.parametrize(
    "attr, is_readme, is_joined",
    [
        ("url", False, False),
        ("solution_url", False, False),
        ("preview", False, False),
        ("readme_url", False, False),
        ("intro_video_url", False, False),
        ("solution_video_url", False, False),
        ("readme_raw", True, False),
        ("readme_raw", True, True),
    ],
)
def test_two_repos_scheduled_and_in_this_execution_was_added_to_the_assets(
    database: capyc.Database, patch_get, attr, is_readme, is_joined
):
    if is_readme and is_joined:
        assets = [
            {
                attr: Asset.encode(
                    "https://github.com/breatheco-de/curso-nodejs-4geeks https://github.com/4GeeksAcademy/curso-nodejs-4geeks"
                ),
            },
        ]
    elif is_readme and is_joined is False:
        assets = [
            {
                attr: Asset.encode("https://github.com/breatheco-de/curso-nodejs-4geeks"),
            },
            {
                attr: Asset.encode("https://github.com/4GeeksAcademy/curso-nodejs-4geeks"),
            },
        ]
    else:
        assets = [
            {
                attr: "https://github.com/breatheco-de/curso-nodejs-4geeks",
            },
            {
                attr: "https://github.com/4GeeksAcademy/curso-nodejs-4geeks",
            },
        ]
    model = database.create(
        academy_auth_settings=1,
        city=1,
        country=1,
        user=1,
        credentials_github=1,
        asset=assets,
        asset_category=1,
        repository_deletion_order=[
            {
                "provider": "GITHUB",
                "repository_name": "curso-nodejs-4geeks",
                "repository_user": "breatheco-de",
                "status": "PENDING",
                "status_text": None,
            },
            {
                "provider": "GITHUB",
                "repository_name": "curso-nodejs-4geeks",
                "repository_user": "4GeeksAcademy",
                "status": "PENDING",
                "status_text": None,
            },
        ],
    )
    patch_get(
        [
            {
                "method": "GET",
                "url": f"https://api.github.com/orgs/{model.academy_auth_settings.github_username}/repos?page=1&type=forks&per_page=30&sort=created&direction=desc",
                "expected": [
                    {
                        "private": False,
                        "html_url": "https://github.com/breatheco-de/curso-nodejs-4geeks",
                        "fork": True,
                        "created_at": "2024-04-05T19:22:39Z",
                        "is_template": False,
                        "allow_forking": True,
                    },
                    {
                        "private": False,
                        "html_url": "https://github.com/4GeeksAcademy/curso-nodejs-4geeks",
                        "fork": True,
                        "created_at": "2024-04-05T19:22:39Z",
                        "is_template": False,
                        "allow_forking": True,
                    },
                ],
                "code": 200,
                "headers": {},
            },
        ]
    )
    command = Command()
    command.handle()

    assert database.list_of("assignments.RepositoryDeletionOrder") == []
    assert database.list_of("assignments.RepositoryWhiteList") == [
        {
            "id": 1,
            "provider": "GITHUB",
            "repository_name": "curso-nodejs-4geeks",
            "repository_user": "breatheco-de",
        },
        {
            "id": 2,
            "provider": "GITHUB",
            "repository_name": "curso-nodejs-4geeks",
            "repository_user": "4GeeksAcademy",
        },
    ]
    assert tasks.send_repository_deletion_notification.delay.call_args_list == []


def test_one_repo__pending__user_found_via_collaborators(
    database: capyc.Database, patch_get, set_datetime, utc_now, format: capyc.Format
):
    """Test that get_username correctly finds and returns a collaborator's username."""
    delta = relativedelta(months=2, hours=1)
    github_username = "4GeeksAcademy"
    collaborator_username = "student-user"
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

    # Make sure we mock every URL pattern needed
    mock_responses = [
        # Get Organization Repos
        {
            "method": "GET",
            "url": f"https://api.github.com/orgs/{model.academy_auth_settings.github_username}/repos?page=1&type=forks&per_page=30&sort=created&direction=desc",
            "expected": [
                {
                    "private": False,
                    "html_url": f"https://github.com/{model.academy_auth_settings.github_username}/curso-nodejs-4geeks",
                    "fork": True,
                    "created_at": "2024-04-05T19:22:39Z",
                    "is_template": False,
                    "allow_forking": True,
                },
            ],
            "code": 200,
            "headers": {},
        },
        # Check if repo exists
        {
            "method": "HEAD",
            "url": f"https://api.github.com/repos/{model.academy_auth_settings.github_username}/curso-nodejs-4geeks",
            "expected": None,
            "code": 200,
            "headers": {},
        },
        # Get collaborators - try both URL patterns
        {
            "method": "GET",
            "url": f"https://api.github.com/repos/{model.academy_auth_settings.github_username}/curso-nodejs-4geeks/collaborators",
            "expected": [
                {
                    "login": collaborator_username,
                    "type": "User",
                    "permissions": {"admin": True, "maintain": True, "push": True, "triage": True, "pull": True},
                }
            ],
            "code": 200,
            "headers": {},
        },
        {
            "method": "GET",
            "url": f"https://api.github.com/repos/{model.academy_auth_settings.github_username}/curso-nodejs-4geeks/collaborators?per_page=30&page=1",
            "expected": [
                {
                    "login": collaborator_username,
                    "type": "User",
                    "permissions": {"admin": True, "maintain": True, "push": True, "triage": True, "pull": True},
                }
            ],
            "code": 200,
            "headers": {},
        },
        # Transfer repo
        {
            "method": "POST",
            "url": f"https://api.github.com/repos/{model.academy_auth_settings.github_username}/curso-nodejs-4geeks/transfer",
            "expected": {"id": 1, "name": "curso-nodejs-4geeks"},
            "code": 202,
            "headers": {},
        },
    ]
    patch_get(mock_responses)

    command = Command()
    command.handle()

    actual_orders = database.list_of("assignments.RepositoryDeletionOrder")
    assert len(actual_orders) == 1

    # Compare important fields
    assert database.list_of("assignments.RepositoryDeletionOrder") == [
        {
            **format.to_obj_repr(model.repository_deletion_order),
            "status": "TRANSFERRING",
            "repository_name": "curso-nodejs-4geeks",
            "repository_user": github_username,
            "starts_transferring_at": utc_now - delta,
        }
    ]

    assert database.list_of("assignments.RepositoryWhiteList") == []
    assert tasks.send_repository_deletion_notification.delay.call_args_list == [
        call(1, collaborator_username),
    ]
