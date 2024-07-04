"""
Test mentorships
"""

import random
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytz
from django.utils import timezone
from pytz import timezone as pytz_timezone

from breathecode.tests.mocks import apply_requests_head_mock

from ...actions import mentor_is_ready
from ..mixins import MentorshipTestCase

BOOKING_URL = "https://calendly.com/abc-xyz"
ONLINE_MEETING_URL = "https://hardcoded.url/abc-xyz"


class GenerateMentorBillsTestCase(MentorshipTestCase):
    """
    🔽🔽🔽 with MentorProfile without online_meeting_url
    """

    @patch(
        "requests.head",
        apply_requests_head_mock(
            [
                (400, BOOKING_URL, None),
                (400, ONLINE_MEETING_URL, None),
            ]
        ),
    )
    def test__without_online_meeting_url(self):
        cases = [{"online_meeting_url": x} for x in [None, ""]]

        for mentor_profile in cases:
            model = self.bc.database.create(mentor_profile=mentor_profile)
            mentor_profile_db = self.bc.format.to_dict(model.mentor_profile)

            with self.assertRaisesMessage(
                Exception,
                f"Mentor {model.mentor_profile.name} does not have backup online_meeting_url, update the "
                "value before activating.",
            ):
                mentor_is_ready(model.mentor_profile)

            self.assertEqual(
                self.bc.database.list_of("mentorship.MentorProfile"),
                [
                    mentor_profile_db,
                ],
            )

            # teardown
            self.bc.database.delete("mentorship.MentorProfile")

    """
    🔽🔽🔽 with MentorProfile with online_meeting_url with bad booking_url
    """

    @patch(
        "requests.head",
        apply_requests_head_mock(
            [
                (400, BOOKING_URL, None),
                (400, ONLINE_MEETING_URL, None),
            ]
        ),
    )
    def test__with_online_meeting_url__with_bad_booking_url(self):
        cases = [
            {
                "online_meeting_url": self.bc.fake.url(),
                "booking_url": x,
            }
            for x in [None, "", self.bc.fake.url()]
        ]

        for mentor_profile in cases:
            model = self.bc.database.create(mentor_profile=mentor_profile)
            mentor_profile_db = self.bc.format.to_dict(model.mentor_profile)

            with self.assertRaisesMessage(
                Exception,
                f"Mentor {model.mentor_profile.name} booking_url must point to calendly, update the "
                "value before activating.",
            ):
                mentor_is_ready(model.mentor_profile)

            self.assertEqual(
                self.bc.database.list_of("mentorship.MentorProfile"),
                [
                    mentor_profile_db,
                ],
            )

            # teardown
            self.bc.database.delete("mentorship.MentorProfile")

    """
    🔽🔽🔽 with MentorProfile with online_meeting_url with booking_url
    """

    @patch(
        "requests.head",
        apply_requests_head_mock(
            [
                (400, BOOKING_URL, None),
                (400, ONLINE_MEETING_URL, None),
            ]
        ),
    )
    def test__with_online_meeting_url__with_booking_url(self):
        mentor_profile = {
            "online_meeting_url": self.bc.fake.url(),
            "booking_url": BOOKING_URL,
        }

        model = self.bc.database.create(mentor_profile=mentor_profile)
        mentor_profile_db = self.bc.format.to_dict(model.mentor_profile)

        with self.assertRaisesMessage(
            Exception,
            f"Mentor {model.mentor_profile.name} has no syllabus associated, update the value before " "activating.",
        ):
            mentor_is_ready(model.mentor_profile)

        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorProfile"),
            [
                mentor_profile_db,
            ],
        )

    """
    🔽🔽🔽 with MentorProfile and Syllabus with online_meeting_url with booking_url
    """

    @patch(
        "requests.head",
        apply_requests_head_mock(
            [
                (400, BOOKING_URL, None),
                (400, ONLINE_MEETING_URL, None),
            ]
        ),
    )
    def test__with_online_meeting_url__with_booking_url__with_syllabus(self):
        mentor_profile = {
            "online_meeting_url": self.bc.fake.url(),
            "booking_url": BOOKING_URL,
            "availability_report": ["bad-booking-url"],
        }

        model = self.bc.database.create(mentor_profile=mentor_profile, syllabus=1)
        mentor_profile_db = self.bc.format.to_dict(model.mentor_profile)

        with self.assertRaisesMessage(Exception, f"Mentor {model.mentor_profile.name} booking URL is failing"):
            mentor_is_ready(model.mentor_profile)

        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorProfile"),
            [
                mentor_profile_db,
            ],
        )

    """
    🔽🔽🔽 with MentorProfile and Syllabus with online_meeting_url with booking_url, booking status 200
    """

    @patch(
        "requests.head",
        apply_requests_head_mock(
            [
                (200, BOOKING_URL, None),
                (400, ONLINE_MEETING_URL, None),
            ]
        ),
    )
    def test__with_online_meeting_url__with_booking_url__with_syllabus__booking_status_200(self):
        mentor_profile = {
            "online_meeting_url": self.bc.fake.url(),
            "booking_url": BOOKING_URL,
            "online_meeting_url": ONLINE_MEETING_URL,
            "availability_report": ["bad-online-meeting-url"],
        }

        model = self.bc.database.create(mentor_profile=mentor_profile, syllabus=1)
        mentor_profile_db = self.bc.format.to_dict(model.mentor_profile)

        with self.assertRaisesMessage(Exception, f"Mentor {model.mentor_profile.name} online meeting URL is failing"):
            mentor_is_ready(model.mentor_profile)

        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorProfile"),
            [
                mentor_profile_db,
            ],
        )

    """
    🔽🔽🔽 with MentorProfile and Syllabus with online_meeting_url with booking_url, booking and online meeting
    status 200
    """

    @patch(
        "requests.head",
        apply_requests_head_mock(
            [
                (200, BOOKING_URL, None),
                (200, ONLINE_MEETING_URL, None),
            ]
        ),
    )
    def test__with_online_meeting_url__with_booking_url__with_syllabus__booking_status_200__online_meeting_status_200(
        self,
    ):
        mentor_profile = {
            "online_meeting_url": self.bc.fake.url(),
            "booking_url": BOOKING_URL,
            "online_meeting_url": ONLINE_MEETING_URL,
        }

        model = self.bc.database.create(mentor_profile=mentor_profile, syllabus=1)
        mentor_profile_db = self.bc.format.to_dict(model.mentor_profile)

        result = mentor_is_ready(model.mentor_profile)

        self.assertTrue(result)
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorProfile"),
            [
                mentor_profile_db,
            ],
        )
