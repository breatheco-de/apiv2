"""
Test /answer
"""

from unittest.mock import MagicMock

import capyc.pytest as capyc
import pytest
from dateutil.relativedelta import relativedelta
from linked_services.django.actions import reset_app_cache

from breathecode.assignments.management.commands.schedule_repository_deletions import Command
from breathecode.registry.models import Asset


@pytest.fixture(autouse=True)
def setup(db):
    reset_app_cache()
    yield


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
        },
        {
            "id": 2,
            "provider": "GITHUB",
            "repository_name": "curso-nodejs-4geeks",
            "repository_user": "4GeeksAcademy",
            "status": "PENDING",
            "status_text": None,
        },
    ]
    assert database.list_of("assignments.RepositoryWhiteList") == []


def test_two_repos__deleting_repositories(database: capyc.Database, patch_get, set_datetime, utc_now):
    from django.utils import timezone

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
        },
        {
            "id": 2,
            "provider": "GITHUB",
            "repository_name": "curso-nodejs-4geeks",
            "repository_user": "4GeeksAcademy",
            "status": "DELETED",
            "status_text": None,
        },
    ]
    assert database.list_of("assignments.RepositoryWhiteList") == []


def test_two_repos__deleting_repositories__got_an_error(database: capyc.Database, patch_get, set_datetime, utc_now):
    from django.utils import timezone

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
            "status_text": "Unable to communicate with Github API for /repos/breatheco-de/curso-nodejs-4geeks, error: 404",
        },
        {
            "id": 2,
            "provider": "GITHUB",
            "repository_name": "curso-nodejs-4geeks",
            "repository_user": "4GeeksAcademy",
            "status": "ERROR",
            "status_text": "Unable to communicate with Github API for /repos/4GeeksAcademy/curso-nodejs-4geeks, error: 404",
        },
    ]
    assert database.list_of("assignments.RepositoryWhiteList") == []


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
