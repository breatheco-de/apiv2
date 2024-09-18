import random

import pytest

from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode
import capyc.pytest as capy


@pytest.mark.parametrize(
    "revision_status, github_url",
    [
        ("PENDING", None),
        ("PENDING", ""),
        ("PENDING", "https://github.com/breathecode-test/test"),
        ("REJECTED", None),
        ("REJECTED", ""),
        ("IGNORED", None),
        ("IGNORED", ""),
        ("APPROVED", None),
        ("APPROVED", ""),
    ],
)
def test_nothing_happens(
    database: capy.Database, format: capy.Format, signals: capy.Signals, revision_status: str, github_url: str
):
    signals.enable("breathecode.assignments.signals.revision_status_updated")

    model = database.create(task={"revision_status": "PENDING", "github_url": github_url})

    if revision_status != "PENDING":
        model.task.revision_status = revision_status
        model.task.save()

    assert database.list_of("assignments.Task") == [
        format.to_obj_repr(model.task),
    ]

    assert database.list_of("assignments.RepositoryDeletionOrder") == []


@pytest.mark.parametrize("revision_status", ["REJECTED", "IGNORED", "APPROVED"])
@pytest.mark.parametrize(
    "github_url, username, repo",
    [
        ("https://github.com/user1/repo1", "user1", "repo1"),
        ("https://github.com/user2/repo2", "user2", "repo2"),
        ("https://github.com/user3/repo3", "user3", "repo3"),
    ],
)
def test_schedule_repository_deletion(
    database: capy.Database,
    format: capy.Format,
    signals: capy.Signals,
    revision_status: str,
    github_url: str,
    username: str,
    repo: str,
):
    signals.enable("breathecode.assignments.signals.revision_status_updated")

    model = database.create(task={"revision_status": "PENDING", "github_url": github_url})

    if revision_status != "PENDING":
        model.task.revision_status = revision_status
        model.task.save()

    assert database.list_of("assignments.Task") == [
        format.to_obj_repr(model.task),
    ]

    assert database.list_of("assignments.RepositoryDeletionOrder") == [
        {
            "id": 1,
            "provider": "GITHUB",
            "repository_name": repo,
            "repository_user": username,
            "status": "PENDING",
            "status_text": None,
        },
    ]
