import random
import pytest
from breathecode.authenticate.management.commands.fix_github_academy_user_logs import Command
from django.utils import timezone

from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode

T1 = timezone.now()
T2 = T1 + timezone.timedelta(days=1)
T3 = T2 + timezone.timedelta(days=1)
T4 = T3 + timezone.timedelta(days=1)

storage_statuses = ["PENDING", "SYNCHED", "ERROR", "UNKNOWN", "PAYMENT_CONFLICT"]
storage_actions = ["ADD", "INVITE", "DELETE", "IGNORE"]


@pytest.fixture(autouse=True)
def setup(db):
    yield


# When: running the command and there are nothing to migrate
# Then: it should don't do anything
def test__nothing_to_migrate(bc: Breathecode):
    command = Command()
    command.handle()

    assert bc.database.list_of("authenticate.GithubAcademyUserLog") == []


# When: Changes the storage_status
# Then: it should link the previous log with the new one
@pytest.mark.parametrize("storage_status", storage_statuses)
@pytest.mark.parametrize(
    "storage_action1,storage_action2,storage_action3",
    [
        (storage_actions[0], storage_actions[1], storage_actions[2]),  # +1
        (storage_actions[0], storage_actions[2], storage_actions[0]),  # +2
        (storage_actions[0], storage_actions[3], storage_actions[2]),  # +3
        #
        (storage_actions[1], storage_actions[2], storage_actions[3]),  # +1
        (storage_actions[1], storage_actions[3], storage_actions[1]),  # +2
        (storage_actions[1], storage_actions[0], storage_actions[3]),  # +3
        #
        (storage_actions[2], storage_actions[3], storage_actions[0]),  # +1
        (storage_actions[2], storage_actions[0], storage_actions[2]),  # +2
        (storage_actions[2], storage_actions[1], storage_actions[0]),  # +3
        #
        (storage_actions[3], storage_actions[0], storage_actions[1]),  # +1
        (storage_actions[3], storage_actions[1], storage_actions[3]),  # +2
        (storage_actions[3], storage_actions[2], storage_actions[1]),  # +3
    ],
)
def test__storage_action_does_not_avoid_the_indexation(
    bc: Breathecode, monkeypatch, storage_status, storage_action1, storage_action2, storage_action3
):

    delta = timezone.timedelta(hours=random.randint(1, 24))
    base_user1 = bc.database.create(user=1, github_academy_user=1)
    base_user2 = bc.database.create(user=1, github_academy_user=1)

    # first status
    github_academy_user_log = {
        "valid_until": None,
        "storage_status": storage_status,
        "storage_action": storage_action1,
    }

    monkeypatch.setattr("django.utils.timezone.now", lambda: T1)
    user1__github_academy_user_log1 = bc.database.create(
        user=base_user1.user,
        academy=base_user1.academy,
        github_academy_user=base_user1.github_academy_user,
        github_academy_user_log=github_academy_user_log,
    ).github_academy_user_log

    monkeypatch.setattr("django.utils.timezone.now", lambda: T1 + delta)
    user2__github_academy_user_log1 = bc.database.create(
        user=base_user2.user,
        github_academy_user=base_user2.github_academy_user,
        github_academy_user_log=github_academy_user_log,
    ).github_academy_user_log

    # second status
    github_academy_user_log["storage_action"] = storage_action2

    monkeypatch.setattr("django.utils.timezone.now", lambda: T2)
    user1__github_academy_user_log2 = bc.database.create(
        user=base_user1.user,
        academy=base_user1.academy,
        github_academy_user=base_user1.github_academy_user,
        github_academy_user_log=github_academy_user_log,
    ).github_academy_user_log

    monkeypatch.setattr("django.utils.timezone.now", lambda: T2 + delta)
    user2__github_academy_user_log2 = bc.database.create(
        user=base_user2.user,
        github_academy_user=base_user2.github_academy_user,
        github_academy_user_log=github_academy_user_log,
    ).github_academy_user_log

    # third status
    github_academy_user_log["storage_action"] = storage_action3

    monkeypatch.setattr("django.utils.timezone.now", lambda: T3)
    user1__github_academy_user_log3 = bc.database.create(
        user=base_user1.user,
        academy=base_user1.academy,
        github_academy_user=base_user1.github_academy_user,
        github_academy_user_log=github_academy_user_log,
    ).github_academy_user_log

    monkeypatch.setattr("django.utils.timezone.now", lambda: T3 + delta)
    user2__github_academy_user_log3 = bc.database.create(
        user=base_user2.user,
        github_academy_user=base_user2.github_academy_user,
        github_academy_user_log=github_academy_user_log,
    ).github_academy_user_log

    command = Command()
    command.handle()

    assert bc.database.list_of("authenticate.GithubAcademyUserLog") == [
        {
            **bc.format.to_dict(user1__github_academy_user_log1),
            "valid_until": T2,
        },
        {
            **bc.format.to_dict(user2__github_academy_user_log1),
            "valid_until": T2 + delta,
        },
        {
            **bc.format.to_dict(user1__github_academy_user_log2),
            "valid_until": T3,
        },
        {
            **bc.format.to_dict(user2__github_academy_user_log2),
            "valid_until": T3 + delta,
        },
        {
            **bc.format.to_dict(user1__github_academy_user_log3),
            "valid_until": None,
        },
        {
            **bc.format.to_dict(user2__github_academy_user_log3),
            "valid_until": None,
        },
    ]


# When: Changes the storage_action
# Then: it should link the previous log with the new one
@pytest.mark.parametrize("storage_action", storage_actions)
@pytest.mark.parametrize(
    "storage_status1,storage_status2,storage_status3",
    [
        (storage_statuses[0], storage_statuses[1], storage_statuses[2]),  # +1
        (storage_statuses[0], storage_statuses[2], storage_statuses[4]),  # +2
        (storage_statuses[0], storage_statuses[3], storage_statuses[1]),  # +3
        (storage_statuses[0], storage_statuses[4], storage_statuses[3]),  # +4
        #
        (storage_statuses[1], storage_statuses[2], storage_statuses[3]),  # +1
        (storage_statuses[1], storage_statuses[3], storage_statuses[0]),  # +2
        (storage_statuses[1], storage_statuses[4], storage_statuses[3]),  # +3
        (storage_statuses[1], storage_statuses[0], storage_statuses[4]),  # +4
        #
        (storage_statuses[2], storage_statuses[3], storage_statuses[4]),  # +1
        (storage_statuses[2], storage_statuses[4], storage_statuses[1]),  # +2
        (storage_statuses[2], storage_statuses[0], storage_statuses[3]),  # +3
        (storage_statuses[2], storage_statuses[1], storage_statuses[0]),  # +4
        #
        (storage_statuses[3], storage_statuses[4], storage_statuses[0]),  # +1
        (storage_statuses[3], storage_statuses[0], storage_statuses[2]),  # +2
        (storage_statuses[3], storage_statuses[1], storage_statuses[4]),  # +3
        (storage_statuses[3], storage_statuses[2], storage_statuses[1]),  # +4
        #
        (storage_statuses[4], storage_statuses[0], storage_statuses[1]),  # +1
        (storage_statuses[4], storage_statuses[1], storage_statuses[3]),  # +2
        (storage_statuses[4], storage_statuses[2], storage_statuses[0]),  # +3
        (storage_statuses[4], storage_statuses[3], storage_statuses[2]),  # +4
    ],
)
def test__storage_status_does_not_avoid_the_indexation(
    bc: Breathecode, monkeypatch, storage_action, storage_status1, storage_status2, storage_status3
):
    delta = timezone.timedelta(hours=random.randint(1, 24))
    base_user1 = bc.database.create(user=1, github_academy_user=1)
    base_user2 = bc.database.create(user=1, github_academy_user=1)

    # first status
    github_academy_user_log = {
        "valid_until": None,
        "storage_status": storage_status1,
        "storage_action": storage_action,
    }

    monkeypatch.setattr("django.utils.timezone.now", lambda: T1)
    user1__github_academy_user_log1 = bc.database.create(
        user=base_user1.user,
        academy=base_user1.academy,
        github_academy_user=base_user1.github_academy_user,
        github_academy_user_log=github_academy_user_log,
    ).github_academy_user_log

    monkeypatch.setattr("django.utils.timezone.now", lambda: T1 + delta)
    user2__github_academy_user_log1 = bc.database.create(
        user=base_user2.user,
        github_academy_user=base_user2.github_academy_user,
        github_academy_user_log=github_academy_user_log,
    ).github_academy_user_log

    # second status
    github_academy_user_log["storage_status"] = storage_status2

    monkeypatch.setattr("django.utils.timezone.now", lambda: T2)
    user1__github_academy_user_log2 = bc.database.create(
        user=base_user1.user,
        academy=base_user1.academy,
        github_academy_user=base_user1.github_academy_user,
        github_academy_user_log=github_academy_user_log,
    ).github_academy_user_log

    monkeypatch.setattr("django.utils.timezone.now", lambda: T2 + delta)
    user2__github_academy_user_log2 = bc.database.create(
        user=base_user2.user,
        github_academy_user=base_user2.github_academy_user,
        github_academy_user_log=github_academy_user_log,
    ).github_academy_user_log

    # third status
    github_academy_user_log["storage_status"] = storage_status3

    monkeypatch.setattr("django.utils.timezone.now", lambda: T3)
    user1__github_academy_user_log3 = bc.database.create(
        user=base_user1.user,
        academy=base_user1.academy,
        github_academy_user=base_user1.github_academy_user,
        github_academy_user_log=github_academy_user_log,
    ).github_academy_user_log

    monkeypatch.setattr("django.utils.timezone.now", lambda: T3 + delta)
    user2__github_academy_user_log3 = bc.database.create(
        user=base_user2.user,
        github_academy_user=base_user2.github_academy_user,
        github_academy_user_log=github_academy_user_log,
    ).github_academy_user_log

    command = Command()
    command.handle()

    assert bc.database.list_of("authenticate.GithubAcademyUserLog") == [
        {
            **bc.format.to_dict(user1__github_academy_user_log1),
            "valid_until": T2,
        },
        {
            **bc.format.to_dict(user2__github_academy_user_log1),
            "valid_until": T2 + delta,
        },
        {
            **bc.format.to_dict(user1__github_academy_user_log2),
            "valid_until": T3,
        },
        {
            **bc.format.to_dict(user2__github_academy_user_log2),
            "valid_until": T3 + delta,
        },
        {
            **bc.format.to_dict(user1__github_academy_user_log3),
            "valid_until": None,
        },
        {
            **bc.format.to_dict(user2__github_academy_user_log3),
            "valid_until": None,
        },
    ]
