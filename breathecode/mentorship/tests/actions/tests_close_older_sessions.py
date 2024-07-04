"""
Test mentorhips
"""

import random
from unittest.mock import patch
from django.utils import timezone
from datetime import timedelta
from unittest.mock import MagicMock, patch

from ..mixins import MentorshipTestCase
from ...actions import close_older_sessions

UTC_NOW = timezone.now()


class GetOrCreateSessionTestSuite(MentorshipTestCase):
    """
    🔽🔽🔽 Without MentorshipSession
    """

    def test_without_mentorship_session(self):
        close_older_sessions()

        self.assertEqual(self.bc.database.list_of("mentorship.MentorshipSession"), [])

    """
    🔽🔽🔽 With two MentorshipSession, all statuses, ends_at less than two hours ago
    """

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_with_two_mentorship_session__all_statuses__ends_at_less_than_two_hours_ago(self):
        statuses = ["PENDING", "STARTED", "COMPLETED", "FAILED", "IGNORED"]

        for current in statuses:
            cases = [
                [
                    {
                        "ends_at": None,
                        "status": current,
                    }
                    for _ in range(0, 2)
                ],
                [
                    {
                        "ends_at": UTC_NOW - timedelta(seconds=random.randint(0, 7200)),  # less than 2 hours
                        "status": current,
                    }
                    for _ in range(0, 2)
                ],
            ]

            for mentorship_sessions in cases:
                model = self.bc.database.create(mentorship_session=mentorship_sessions)

                close_older_sessions()

                self.assertEqual(
                    self.bc.database.list_of("mentorship.MentorshipSession"),
                    [
                        self.bc.format.to_dict(model.mentorship_session[0]),
                        self.bc.format.to_dict(model.mentorship_session[1]),
                    ],
                )

                # teardown
                self.bc.database.delete("mentorship.MentorshipSession")

    """
    🔽🔽🔽 With two MentorshipSession, unfinished statuses, ends_at two hours ago or more
    """

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_with_two_mentorship_session__unfinished_statuses__ends_at_two_hours_ago_or_more(self):
        statuses = ["PENDING", "STARTED"]
        for current in statuses:
            mentorship_sessions = [
                {
                    "ends_at": UTC_NOW - timedelta(seconds=random.randint(7201, 10000)),  # eq or gt than 2 hours
                    "status": current,
                }
                for _ in range(0, 2)
            ]

            model = self.bc.database.create(mentorship_session=mentorship_sessions)

            close_older_sessions()

            self.assertEqual(
                self.bc.database.list_of("mentorship.MentorshipSession"),
                [
                    {
                        **self.bc.format.to_dict(model.mentorship_session[0]),
                        "status": "FAILED",
                        "summary": "Automatically closed because its ends was two hours ago or more",
                        "ended_at": UTC_NOW,
                    },
                    {
                        **self.bc.format.to_dict(model.mentorship_session[1]),
                        "status": "FAILED",
                        "summary": "Automatically closed because its ends was two hours ago or more",
                        "ended_at": UTC_NOW,
                    },
                ],
            )

            # teardown
            self.bc.database.delete("mentorship.MentorshipSession")

    """
    🔽🔽🔽 With two MentorshipSession, finished statuses, ends_at two hours ago or more
    """

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_with_two_mentorship_session__finished_statuses__ends_at_two_hours_ago_or_more(self):
        statuses = ["COMPLETED", "FAILED", "IGNORED"]
        for current in statuses:
            mentorship_sessions = [
                {
                    "ends_at": UTC_NOW - timedelta(seconds=random.randint(7201, 10000)),  # eq or gt than 2 hours
                    "status": current,
                }
                for _ in range(0, 2)
            ]

            model = self.bc.database.create(mentorship_session=mentorship_sessions)

            close_older_sessions()

            self.assertEqual(
                self.bc.database.list_of("mentorship.MentorshipSession"),
                [
                    {
                        **self.bc.format.to_dict(model.mentorship_session[0]),
                    },
                    {
                        **self.bc.format.to_dict(model.mentorship_session[1]),
                    },
                ],
            )

            # teardown
            self.bc.database.delete("mentorship.MentorshipSession")
