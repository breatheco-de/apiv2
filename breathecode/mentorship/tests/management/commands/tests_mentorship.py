"""
This file just can contains duck tests refert to AcademyInviteView
"""

from unittest.mock import MagicMock, call

import pytest
from django.utils import timezone

from breathecode.mentorship.management.commands.mentorship import Command
from breathecode.mentorship.tasks import check_mentorship_profile
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode

UTC_NOW = timezone.now()


@pytest.fixture(autouse=True)
def setup(db, monkeypatch):
    monkeypatch.setattr(check_mentorship_profile, "delay", MagicMock())
    yield


def test_no_mentors(bc: Breathecode):
    command = Command()
    command.handle()

    assert check_mentorship_profile.delay.call_args_list == []


@pytest.mark.parametrize("status", ["ACTIVE", "UNLISTED"])
def test_valid_statuses(bc: Breathecode, status):
    model = bc.database.create(mentor_profile=(3, {"status": status}))

    command = Command()
    command.handle()

    assert check_mentorship_profile.delay.call_args_list == [call(n) for n in range(1, 4)]
    assert bc.database.list_of("mentorship.MentorProfile") == bc.format.to_dict(model.mentor_profile)


@pytest.mark.parametrize("status", ["INNACTIVE", "INVITED"])
def test_wrong_statuses(bc: Breathecode, status):
    model = bc.database.create(mentor_profile=(3, {"status": status}))

    command = Command()
    command.handle()

    assert check_mentorship_profile.delay.call_args_list == []
    assert bc.database.list_of("mentorship.MentorProfile") == bc.format.to_dict(model.mentor_profile)
