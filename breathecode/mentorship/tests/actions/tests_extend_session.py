"""
Test mentorships
"""

from datetime import datetime, timedelta
import random
from unittest.mock import patch
from django.utils import timezone
from unittest.mock import MagicMock, patch
from pytz import timezone as pytz_timezone

import pytz

from breathecode.mentorship.exceptions import ExtendSessionException
from breathecode.tests.mocks import apply_requests_request_mock

from ..mixins import MentorshipTestCase
from ...actions import extend_session

NOW = timezone.now()


def apply_get_env(envs={}):

    def get_env(key, default=None):
        return envs.get(key, default)

    return get_env


ENV = {"DAILY_API_URL": "https://netscape.bankruptcy.story"}
SESSION_NAME = "luxray"
URL = f"https://netscape.bankruptcy.story/v1/rooms/{SESSION_NAME}"
DATA = {"x": 2}


class GenerateMentorBillsTestCase(MentorshipTestCase):
    """
    🔽🔽🔽 without MentorshipSession without name
    """

    @patch("os.getenv", MagicMock(side_effect=apply_get_env(ENV)))
    def test__without_name(self):

        model = self.bc.database.create(mentorship_session=1)

        with self.assertRaisesMessage(ExtendSessionException, "Can't extend sessions not have a name"):
            extend_session(model.mentorship_session)

        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipSession"),
            [
                self.bc.format.to_dict(model.mentorship_session),
            ],
        )

    """
    🔽🔽🔽 without MentorshipSession without name and ends_at
    """

    @patch("os.getenv", MagicMock(side_effect=apply_get_env(ENV)))
    @patch("requests.request", apply_requests_request_mock([(201, URL, DATA)]))
    def test__with_name__without_ends_at(self):

        mentorship_session = {"name": SESSION_NAME}
        model = self.bc.database.create(mentorship_session=mentorship_session)
        mentorship_session_db = self.bc.format.to_dict(model.mentorship_session)

        result = extend_session(model.mentorship_session)

        self.bc.check.queryset_with_pks(result, [1])
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipSession"),
            [
                mentorship_session_db,
            ],
        )

    """
    🔽🔽🔽 without MentorshipSession without name with ends_at
    """

    @patch("os.getenv", MagicMock(side_effect=apply_get_env(ENV)))
    @patch("requests.request", apply_requests_request_mock([(201, URL, DATA)]))
    def test__with_name____with_ends_at(self):

        now = timezone.now()
        mentorship_session = {"name": SESSION_NAME, "ends_at": now}
        model = self.bc.database.create(mentorship_session=mentorship_session)
        mentorship_session_db = self.bc.format.to_dict(model.mentorship_session)

        result = extend_session(model.mentorship_session)

        self.bc.check.queryset_with_pks(result, [1])
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipSession"),
            [
                {
                    **mentorship_session_db,
                    "ends_at": now + timedelta(minutes=30),
                },
            ],
        )

    """
    🔽🔽🔽 without MentorshipSession without name with ends_at, passing duration_in_minutes
    """

    @patch("os.getenv", MagicMock(side_effect=apply_get_env(ENV)))
    @patch("requests.request", apply_requests_request_mock([(201, URL, DATA)]))
    def test__with_name____with_ends_at__passing_duration_in_minutes(self):

        now = timezone.now()
        duration_in_minutes = random.randint(1, 1000)
        mentorship_session = {"name": SESSION_NAME, "ends_at": now}
        model = self.bc.database.create(mentorship_session=mentorship_session)
        mentorship_session_db = self.bc.format.to_dict(model.mentorship_session)

        result = extend_session(model.mentorship_session, duration_in_minutes=duration_in_minutes)

        self.bc.check.queryset_with_pks(result, [1])
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipSession"),
            [
                {
                    **mentorship_session_db,
                    "ends_at": now + timedelta(minutes=duration_in_minutes),
                },
            ],
        )

    """
    🔽🔽🔽 without MentorshipSession without name with ends_at, passing exp_in_epoch
    """

    @patch("os.getenv", MagicMock(side_effect=apply_get_env(ENV)))
    @patch("requests.request", apply_requests_request_mock([(201, URL, DATA)]))
    def test__with_name____with_ends_at__passing_exp_in_epoch(self):

        now = timezone.now()
        diff = timedelta(minutes=random.randint(1, 1000))
        timestamp = datetime.timestamp(now + diff)

        mentorship_session = {"name": SESSION_NAME, "ends_at": now}
        model = self.bc.database.create(mentorship_session=mentorship_session)
        mentorship_session_db = self.bc.format.to_dict(model.mentorship_session)

        result = extend_session(model.mentorship_session, exp_in_epoch=timestamp)

        self.bc.check.queryset_with_pks(result, [1])
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipSession"),
            [
                {
                    **mentorship_session_db,
                    "ends_at": now + diff,
                },
            ],
        )

    """
    🔽🔽🔽 without MentorshipSession without name with ends_at, passing exp_in_epoch and tz
    """

    @patch("os.getenv", MagicMock(side_effect=apply_get_env(ENV)))
    @patch("requests.request", apply_requests_request_mock([(201, URL, DATA)]))
    def test__with_name____with_ends_at__passing_exp_in_epoch__passing_tz(self):

        timezones = []
        for _ in range(0, 10):
            possibilities = [x for x in pytz.all_timezones if x not in timezones]
            timezones.append(random.choice(possibilities))

        for current in timezones:
            tz = pytz_timezone(current)
            now = timezone.now().replace(tzinfo=tz)

            diff = timedelta(minutes=random.randint(1, 1000))
            timestamp = datetime.timestamp(now + diff)

            mentorship_session = {"name": SESSION_NAME, "ends_at": now}
            model = self.bc.database.create(mentorship_session=mentorship_session)
            mentorship_session_db = self.bc.format.to_dict(model.mentorship_session)

            result = extend_session(model.mentorship_session, exp_in_epoch=timestamp, tz=tz)

            self.bc.check.queryset_with_pks(result, [model.mentorship_session.id])
            self.assertEqual(
                self.bc.database.list_of("mentorship.MentorshipSession"),
                [
                    {
                        **mentorship_session_db,
                        "ends_at": now + diff,
                    },
                ],
            )

            # teardown
            self.bc.database.delete("mentorship.MentorshipSession")
