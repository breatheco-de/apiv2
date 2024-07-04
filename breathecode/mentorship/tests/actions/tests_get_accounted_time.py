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
from ...actions import get_accounted_time, duration_to_str

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
    🔽🔽🔽 without MentorshipSession without started_at and mentor_joined_at
    """

    def test__without_started_at__without_mentor_joined_at(self):
        mentorship_session = {
            "started_at": None,
            "mentor_joined_at": None,
        }
        mentorship_service = {"missed_meeting_duration": timedelta(minutes=10)}
        model = self.bc.database.create(mentorship_session=mentorship_session, mentorship_service=mentorship_service)
        mentorship_session_db = self.bc.format.to_dict(model.mentorship_session)

        result = get_accounted_time(model.mentorship_session)
        expected = {
            "accounted_duration": timedelta(0),
            "status_message": "No one joined this session, nothing will be accounted for.",
        }

        self.assertEqual(result, expected)
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipSession"),
            [
                mentorship_session_db,
            ],
        )

    """
    🔽🔽🔽 without MentorshipSession without started_at and with mentor_joined_at
    """

    def test__without_started_at__with_mentor_joined_at__with_missed_meeting_duration_eq_zero(self):
        now = timezone.now()
        mentorship_session = {
            "started_at": None,
            "mentor_joined_at": now,
        }
        mentorship_service = {"missed_meeting_duration": timedelta(minutes=0)}
        model = self.bc.database.create(mentorship_session=mentorship_session, mentorship_service=mentorship_service)
        mentorship_session_db = self.bc.format.to_dict(model.mentorship_session)

        result = get_accounted_time(model.mentorship_session)
        expected = {
            "accounted_duration": timedelta(0),
            "status_message": "Mentor joined but mentee never did, No time will be included on the bill.",
        }

        self.assertEqual(result, expected)
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipSession"),
            [
                mentorship_session_db,
            ],
        )

    """
    🔽🔽🔽 without MentorshipSession without started_at and with mentor_joined_at
    """

    def test__without_started_at__with_mentor_joined_at__with_missed_meeting_duration_eq_ten(self):
        now = timezone.now()
        mentorship_session = {
            "started_at": None,
            "mentor_joined_at": now,
        }
        mentorship_service = {"missed_meeting_duration": timedelta(minutes=10)}
        model = self.bc.database.create(mentorship_session=mentorship_session, mentorship_service=mentorship_service)
        mentorship_session_db = self.bc.format.to_dict(model.mentorship_session)

        result = get_accounted_time(model.mentorship_session)
        expected = {
            "accounted_duration": timedelta(seconds=600),
            "status_message": "Mentor joined but mentee never did, 10 min will be accounted for the bill.",
        }

        self.assertEqual(result, expected)
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipSession"),
            [
                mentorship_session_db,
            ],
        )

    """
    🔽🔽🔽 without MentorshipSession with started_at and without mentor_joined_at
    """

    def test__with_started_at__without_mentor_joined_at(self):
        now = timezone.now()
        mentorship_session = {
            "started_at": now,
            "mentor_joined_at": None,
        }
        mentorship_service = {"missed_meeting_duration": timedelta(minutes=10)}
        model = self.bc.database.create(mentorship_session=mentorship_session, mentorship_service=mentorship_service)
        mentorship_session_db = self.bc.format.to_dict(model.mentorship_session)

        result = get_accounted_time(model.mentorship_session)
        expected = {
            "accounted_duration": timedelta(0),
            "status_message": "The mentor never joined the meeting, no time will be accounted for.",
        }

        self.assertEqual(result, expected)
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipSession"),
            [
                mentorship_session_db,
            ],
        )

    """
    🔽🔽🔽 without MentorshipSession with started_at and mentor_joined_at
    """

    def test__with_started_at__with_mentor_joined_at(self):
        now = timezone.now()
        mentorship_session = {
            "started_at": now,
            "mentor_joined_at": now,
        }
        mentorship_service = {"missed_meeting_duration": timedelta(minutes=10)}
        model = self.bc.database.create(mentorship_session=mentorship_session, mentorship_service=mentorship_service)
        mentorship_session_db = self.bc.format.to_dict(model.mentorship_session)

        result = get_accounted_time(model.mentorship_session)
        expected = {
            "accounted_duration": timedelta(seconds=3600),
            "status_message": "The session never ended, accounting for the standard duration 1 hr.",
        }

        self.assertEqual(result, expected)
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipSession"),
            [
                mentorship_session_db,
            ],
        )

    """
    🔽🔽🔽 without MentorshipSession with started_at, mentor_joined_at and ends_at
    """

    def test__with_started_at__with_mentor_joined_at__with_ends_at(self):
        cases = [random.randint(0, 1000) for _ in range(0, 5)]
        for n in cases:
            now = timezone.now()
            diff = timedelta(seconds=n)
            mentorship_session = {
                "started_at": now,
                "mentor_joined_at": now,
                "ends_at": now + diff,
            }
            mentorship_service = {"missed_meeting_duration": timedelta(minutes=10)}
            model = self.bc.database.create(
                mentorship_session=mentorship_session, mentorship_service=mentorship_service
            )
            mentorship_session_db = self.bc.format.to_dict(model.mentorship_session)

            result = get_accounted_time(model.mentorship_session)
            expected = {
                "accounted_duration": diff,
                "status_message": (
                    "The session never ended, accounting for the expected meeting duration "
                    f"that was {duration_to_str(diff)}."
                ),
            }

            self.assertEqual(result, expected)
            self.assertEqual(
                self.bc.database.list_of("mentorship.MentorshipSession"),
                [
                    mentorship_session_db,
                ],
            )

            # teardown
            self.bc.database.delete("mentorship.MentorshipSession")

    """
    🔽🔽🔽 without MentorshipSession with started_at, mentor_joined_at and mentee_left_at
    """

    def test__with_started_at__with_mentor_joined_at__with_mentee_left_at(self):
        cases = [random.randint(0, 1000) for _ in range(0, 5)]
        for n in cases:
            now = timezone.now()
            diff = timedelta(seconds=n)
            mentorship_session = {
                "started_at": now,
                "mentor_joined_at": now,
                "mentee_left_at": now + diff,
            }
            mentorship_service = {"missed_meeting_duration": timedelta(minutes=10)}
            model = self.bc.database.create(
                mentorship_session=mentorship_session, mentorship_service=mentorship_service
            )
            mentorship_session_db = self.bc.format.to_dict(model.mentorship_session)

            result = get_accounted_time(model.mentorship_session)
            expected = {
                "accounted_duration": diff,
                "status_message": (
                    "The session never ended, accounting duration based on the time where "
                    f"the mentee left the meeting {duration_to_str(diff)}."
                ),
            }

            self.assertEqual(result, expected)
            self.assertEqual(
                self.bc.database.list_of("mentorship.MentorshipSession"),
                [
                    mentorship_session_db,
                ],
            )

            # teardown
            self.bc.database.delete("mentorship.MentorshipSession")

    """
    🔽🔽🔽 without MentorshipSession with started_at, mentor_joined_at and mentor_left_at
    """

    def test__with_started_at__with_mentor_joined_at__with_mentor_left_at(self):
        cases = [random.randint(0, 1000) for _ in range(0, 5)]
        for n in cases:
            now = timezone.now()
            diff = timedelta(seconds=n)
            mentorship_session = {
                "started_at": now,
                "mentor_joined_at": now,
                "mentor_left_at": now + diff,
            }
            mentorship_service = {"missed_meeting_duration": timedelta(minutes=10)}
            model = self.bc.database.create(
                mentorship_session=mentorship_session, mentorship_service=mentorship_service
            )
            mentorship_session_db = self.bc.format.to_dict(model.mentorship_session)

            result = get_accounted_time(model.mentorship_session)
            expected = {
                "accounted_duration": diff,
                "status_message": (
                    "The session never ended, accounting duration based on the time where "
                    f"the mentor left the meeting {duration_to_str(diff)}."
                ),
            }

            self.assertEqual(result, expected)
            self.assertEqual(
                self.bc.database.list_of("mentorship.MentorshipSession"),
                [
                    mentorship_session_db,
                ],
            )

            # teardown
            self.bc.database.delete("mentorship.MentorshipSession")

    """
    🔽🔽🔽 without MentorshipSession with started_at, mentor_joined_at and ended_at, ended in the pass
    """

    def test__with_started_at__with_mentor_joined_at__with_ended_at__ended_in_the_pass(self):
        now = timezone.now()
        mentorship_session = {
            "started_at": now,
            "mentor_joined_at": now,
            "ended_at": now - timedelta(seconds=1),
        }
        mentorship_service = {"missed_meeting_duration": timedelta(minutes=10)}
        model = self.bc.database.create(mentorship_session=mentorship_session, mentorship_service=mentorship_service)
        mentorship_session_db = self.bc.format.to_dict(model.mentorship_session)

        result = get_accounted_time(model.mentorship_session)
        expected = {
            "accounted_duration": timedelta(0),
            "status_message": "Meeting started before it ended? No duration will be accounted for.",
        }

        self.assertEqual(result, expected)
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipSession"),
            [
                mentorship_session_db,
            ],
        )

    """
    🔽🔽🔽 without MentorshipSession with started_at, mentor_joined_at and ended_at, one days of duration
    """

    def test__with_started_at__with_mentor_joined_at__with_ended_at__one_days_of_duration(self):
        now = timezone.now()
        mentorship_session = {
            "started_at": now,
            "mentor_joined_at": now,
            "ended_at": now + timedelta(days=1),
        }
        mentorship_service = {"missed_meeting_duration": timedelta(minutes=10)}
        model = self.bc.database.create(mentorship_session=mentorship_session, mentorship_service=mentorship_service)
        mentorship_session_db = self.bc.format.to_dict(model.mentorship_session)

        result = get_accounted_time(model.mentorship_session)
        expected = {
            "accounted_duration": timedelta(seconds=3600),
            "status_message": (
                "This session lasted more than a day, no one ever left, was probably never "
                "closed, accounting for standard duration 1 hr."
            ),
        }

        self.assertEqual(result, expected)
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipSession"),
            [
                mentorship_session_db,
            ],
        )

    """
    🔽🔽🔽 without MentorshipSession with started_at, mentor_joined_at, ended_at and mentee_left_at, one days of
    duration
    """

    def test__with_started_at__with_mentor_joined_at__with_ended_at__with_mentee_left_at__one_days_of_duration(self):
        now = timezone.now()
        diff = timedelta(seconds=random.randint(0, 10000))
        mentorship_session = {
            "started_at": now,
            "mentor_joined_at": now,
            "mentee_left_at": now + diff,
            "ended_at": now + timedelta(days=1),
        }
        mentorship_service = {"missed_meeting_duration": timedelta(minutes=10)}
        model = self.bc.database.create(mentorship_session=mentorship_session, mentorship_service=mentorship_service)
        mentorship_session_db = self.bc.format.to_dict(model.mentorship_session)

        result = get_accounted_time(model.mentorship_session)
        extended_message = (
            " The session accounted duration was limited to the maximum allowed "
            f"{duration_to_str(model.mentorship_service.max_duration)}."
        )
        maximum = timedelta(hours=2)
        expected = {
            "accounted_duration": diff if diff < maximum else maximum,
            "status_message": (
                "The lasted way more than it should, accounting duration based on the time "
                f"where the mentee left the meeting {duration_to_str(diff)}."
            ),
        }

        if diff > model.mentorship_service.max_duration:
            expected["status_message"] += extended_message

        self.assertEqual(result, expected)
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipSession"),
            [
                mentorship_session_db,
            ],
        )

    """
    🔽🔽🔽 without MentorshipSession with started_at, mentor_joined_at and ended_at, less one days of duration,
    with max max_duration
    """

    def test__with_started_at__with_mentor_joined_at__with_ended_at__less_one_days_of_duration__with_max_duration(self):
        now = timezone.now()
        mentorship_session = {
            "started_at": now,
            "mentor_joined_at": now,
            "ended_at": now + timedelta(seconds=random.randint(7201, 85399)),  # less one day
        }
        mentorship_service = {"missed_meeting_duration": timedelta(minutes=10)}
        model = self.bc.database.create(mentorship_session=mentorship_session, mentorship_service=mentorship_service)
        mentorship_session_db = self.bc.format.to_dict(model.mentorship_session)

        result = get_accounted_time(model.mentorship_session)
        expected = {
            "accounted_duration": model.mentorship_service.max_duration,
            "status_message": (
                "The duration of the session is bigger than the maximum allowed, accounting "
                "for max duration of "
                f"{duration_to_str(model.mentorship_service.max_duration)}."
            ),
        }

        self.assertEqual(result, expected)
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipSession"),
            [
                mentorship_session_db,
            ],
        )

    """
    🔽🔽🔽 without MentorshipSession with started_at, mentor_joined_at and ended_at, less one days of duration,
    without max_duration
    """

    def test__with_started_at__with_mentor_joined_at__with_ended_at__less_one_days_of_duration__without_max_duration(
        self,
    ):
        now = timezone.now()
        diff = timedelta(seconds=random.randint(0, 85399))  # less one day
        mentorship_session = {
            "started_at": now,
            "mentor_joined_at": now,
            "ended_at": now + diff,
        }
        mentorship_service = {"missed_meeting_duration": timedelta(minutes=10), "max_duration": timedelta(0)}
        model = self.bc.database.create(mentorship_session=mentorship_session, mentorship_service=mentorship_service)
        mentorship_session_db = self.bc.format.to_dict(model.mentorship_session)

        result = get_accounted_time(model.mentorship_session)
        extended_message = (
            " The session accounted duration was limited to the maximum allowed "
            f"{duration_to_str(model.mentorship_service.max_duration)}."
        )
        expected = {
            "accounted_duration": model.mentorship_service.max_duration,
            "status_message": (
                "No extra time is allowed for session, accounting for standard duration of "
                f"{duration_to_str(model.mentorship_service.duration)}." + extended_message
            ),
        }

        self.assertEqual(result, expected)
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipSession"),
            [
                mentorship_session_db,
            ],
        )
