"""
Test mentorships
"""

import datetime
from unittest.mock import MagicMock, patch

import pytz

from capyc.rest_framework.exceptions import ValidationException

from ...actions import generate_mentor_bills
from ..mixins import MentorshipTestCase

NOW = datetime.datetime(year=2022, month=1, day=5, hour=0, minute=0, second=0, microsecond=0, tzinfo=pytz.UTC)


def mentorship_bill_field(data={}):
    return {
        "academy_id": 0,
        "ended_at": None,
        "id": 0,
        "mentor_id": 0,
        "overtime_minutes": 0.0,
        "paid_at": None,
        "reviewer_id": None,
        "started_at": None,
        "status": "DUE",
        "status_mesage": None,
        "total_duration_in_hours": 0.0,
        "total_duration_in_minutes": 0.0,
        "total_price": 0.0,
        **data,
    }


def mentorship_session_field(data={}):
    return {
        "name": None,
        "is_online": False,
        "latitude": None,
        "longitude": None,
        "mentor_id": 0,
        "service_id": None,
        "calendly_uuid": None,
        "mentee_id": None,
        "online_meeting_url": None,
        "online_recording_url": None,
        "status": "PENDING",
        "status_message": None,
        "allow_billing": True,
        "bill_id": None,
        "accounted_duration": None,
        "agenda": None,
        "summary": None,
        "starts_at": None,
        "ends_at": None,
        "started_at": None,
        "ended_at": None,
        "mentor_joined_at": None,
        "mentor_left_at": None,
        "mentee_left_at": None,
        "suggested_accounted_duration": None,
        "questions_and_answers": None,
        **data,
    }


class GenerateMentorBillsTestCase(MentorshipTestCase):

    @patch("django.utils.timezone.now", MagicMock(return_value=NOW))
    def test_generate_bills_with_no_previous_bills_no_unpaid_sessions__session_without_service(self):
        """
        First bill generate, with no previous bills.
        """

        models = self.bc.database.create(mentor_profile=1, user=1, mentorship_session=1)
        mentor = models.mentor_profile

        with self.assertRaisesMessage(ValidationException, "session_without_service"):
            generate_mentor_bills(mentor)

        self.assertEqual(self.bc.database.list_of("mentorship.MentorshipBill"), [])
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipSession"),
            [
                self.bc.format.to_dict(models.mentorship_session),
            ],
        )

    @patch("django.utils.timezone.now", MagicMock(return_value=NOW))
    def test_generate_bills_with_no_previous_bills_no_unpaid_sessions__session_with_service(self):
        """
        First bill generate, with no previous bills.
        """

        models = self.bc.database.create(mentor_profile=1, user=1, mentorship_session=1, mentorship_service=1)
        mentor = models.mentor_profile

        bills = generate_mentor_bills(mentor)

        self.assertEqual(bills, [])

        self.assertEqual(self.bc.database.list_of("mentorship.MentorshipBill"), [])
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipSession"),
            [
                self.bc.format.to_dict(models.mentorship_session),
            ],
        )

    @patch("django.utils.timezone.now", MagicMock(return_value=NOW))
    @patch("breathecode.notify.actions.send_email_message", MagicMock())
    def test_generate_bills_with_no_previous_bills_pending_sessions(self):
        """
        Generate bills with no previous billing history and 3 previous sessions
        """

        models_a = self.bc.database.create(
            mentor_profile=1,
            user=1,
            mentorship_service=1,
            mentorship_session={
                "status": "COMPLETED",
                "started_at": datetime.datetime(2021, 10, 16, 22, 0, tzinfo=pytz.UTC),
                "ended_at": datetime.datetime(2021, 10, 16, 23, 0, tzinfo=pytz.UTC),
                "accounted_duration": datetime.timedelta(hours=1),
            },
        )
        models = self.bc.database.create(
            mentor_profile=1,
            user=1,
            mentorship_service=1,
            mentorship_session=[
                {
                    "status": "COMPLETED",
                    "started_at": datetime.datetime(2021, 10, 16, 22, 0, tzinfo=pytz.UTC),
                    "ended_at": datetime.datetime(2021, 10, 16, 23, 0, tzinfo=pytz.UTC),
                    "accounted_duration": datetime.timedelta(hours=1),
                },
                {
                    "status": "COMPLETED",
                    "started_at": datetime.datetime(2021, 10, 17, 21, 0, tzinfo=pytz.UTC),
                    "ended_at": datetime.datetime(2021, 10, 17, 23, 0, tzinfo=pytz.UTC),
                    "accounted_duration": datetime.timedelta(hours=2),
                },
                {
                    "status": "COMPLETED",
                    "started_at": datetime.datetime(2021, 11, 25, 21, 0, tzinfo=pytz.UTC),
                    "ended_at": datetime.datetime(2021, 11, 25, 23, 0, tzinfo=pytz.UTC),
                    "accounted_duration": datetime.timedelta(hours=2),
                },
            ],
        )
        mentor = models.mentor_profile

        bills = generate_mentor_bills(mentor)

        list_bills = [self.bc.format.to_dict(x) for x in bills]
        first = sorted(models.mentorship_session, key=lambda x: x.started_at)[0].started_at
        latest = sorted(models.mentorship_session, key=lambda x: x.ended_at, reverse=True)[0].ended_at

        bill1 = (
            round(models_a.mentorship_session.accounted_duration.seconds / 60 / 60, 2)
            * models.mentor_profile.price_per_hour
        )

        bill2 = (
            round(
                (
                    models.mentorship_session[0].accounted_duration.seconds
                    + models.mentorship_session[1].accounted_duration.seconds
                )
                / 60
                / 60,
                2,
            )
            * models.mentor_profile.price_per_hour
        )

        bill3 = (
            round((models.mentorship_session[2].accounted_duration.seconds) / 60 / 60, 2)
            * models.mentor_profile.price_per_hour
        )

        self.assertEqual(
            list_bills,
            [
                mentorship_bill_field(
                    {
                        "academy_id": 2,
                        "started_at": datetime.datetime(2021, 10, 1, 0, 0, 0, 0, tzinfo=pytz.UTC),
                        "ended_at": datetime.datetime(2021, 10, 31, 23, 59, 59, 999999, tzinfo=pytz.UTC),
                        "id": 1,
                        "mentor_id": 2,
                        "overtime_minutes": 60.0,
                        "total_duration_in_hours": 3.0,
                        "total_duration_in_minutes": 180.0,
                        "total_price": bill2,
                    }
                ),
                mentorship_bill_field(
                    {
                        "academy_id": 2,
                        "started_at": datetime.datetime(2021, 11, 1, 0, 0, 0, 0, tzinfo=pytz.UTC),
                        "ended_at": datetime.datetime(2021, 11, 30, 23, 59, 59, 999999, tzinfo=pytz.UTC),
                        "id": 2,
                        "mentor_id": 2,
                        "overtime_minutes": 60.0,
                        "total_duration_in_hours": 2.0,
                        "total_duration_in_minutes": 120.0,
                        "total_price": bill3,
                    }
                ),
            ],
        )

        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipBill"),
            [
                mentorship_bill_field(
                    {
                        "academy_id": 2,
                        "started_at": datetime.datetime(2021, 10, 1, 0, 0, 0, 0, tzinfo=pytz.UTC),
                        "ended_at": datetime.datetime(2021, 10, 31, 23, 59, 59, 999999, tzinfo=pytz.UTC),
                        "id": 1,
                        "mentor_id": 2,
                        "overtime_minutes": 60.0,
                        "total_duration_in_hours": 3.0,
                        "total_duration_in_minutes": 180.0,
                        "total_price": bill2,
                    }
                ),
                mentorship_bill_field(
                    {
                        "academy_id": 2,
                        "started_at": datetime.datetime(2021, 11, 1, 0, 0, 0, 0, tzinfo=pytz.UTC),
                        "ended_at": datetime.datetime(2021, 11, 30, 23, 59, 59, 999999, tzinfo=pytz.UTC),
                        "id": 2,
                        "mentor_id": 2,
                        "overtime_minutes": 60.0,
                        "total_duration_in_hours": 2.0,
                        "total_duration_in_minutes": 120.0,
                        "total_price": bill3,
                    }
                ),
            ],
        )

        status_message = "The mentor never joined the meeting, no time will be " "accounted for."

        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipSession"),
            [
                mentorship_session_field(
                    {
                        "accounted_duration": datetime.timedelta(seconds=3600),
                        "id": 1,
                        "mentee_id": 1,
                        "mentor_id": 1,
                        "service_id": 1,
                        "status": "COMPLETED",
                        "started_at": datetime.datetime(2021, 10, 16, 22, 0, tzinfo=pytz.UTC),
                        "ended_at": datetime.datetime(2021, 10, 16, 23, 0, tzinfo=pytz.UTC),
                        "bill_id": None,
                    }
                ),
                mentorship_session_field(
                    {
                        "accounted_duration": datetime.timedelta(seconds=3600),
                        "id": 2,
                        "mentee_id": 2,
                        "mentor_id": 2,
                        "service_id": 2,
                        "status": "COMPLETED",
                        "status_message": status_message,
                        "suggested_accounted_duration": datetime.timedelta(0),
                        "started_at": datetime.datetime(2021, 10, 16, 22, 0, tzinfo=pytz.UTC),
                        "ended_at": datetime.datetime(2021, 10, 16, 23, 0, tzinfo=pytz.UTC),
                        "summary": None,
                        "bill_id": 1,
                    }
                ),
                mentorship_session_field(
                    {
                        "accounted_duration": datetime.timedelta(seconds=7200),
                        "id": 3,
                        "mentee_id": 2,
                        "mentor_id": 2,
                        "service_id": 2,
                        "status": "COMPLETED",
                        "status_message": status_message,
                        "suggested_accounted_duration": datetime.timedelta(0),
                        "started_at": datetime.datetime(2021, 10, 17, 21, 0, tzinfo=pytz.UTC),
                        "ended_at": datetime.datetime(2021, 10, 17, 23, 0, tzinfo=pytz.UTC),
                        "summary": None,
                        "bill_id": 1,
                    }
                ),
                mentorship_session_field(
                    {
                        "accounted_duration": datetime.timedelta(seconds=7200),
                        "id": 4,
                        "mentee_id": 2,
                        "mentor_id": 2,
                        "service_id": 2,
                        "status": "COMPLETED",
                        "status_message": status_message,
                        "suggested_accounted_duration": datetime.timedelta(0),
                        "started_at": datetime.datetime(2021, 11, 25, 21, 0, tzinfo=pytz.UTC),
                        "ended_at": datetime.datetime(2021, 11, 25, 23, 0, tzinfo=pytz.UTC),
                        "summary": None,
                        "bill_id": 2,
                    }
                ),
            ],
        )

    @patch("django.utils.timezone.now", MagicMock(return_value=NOW))
    @patch("breathecode.notify.actions.send_email_message", MagicMock())
    def test_generate_bills_with_previous_bills_and_pending_sessions__status_due(self):
        """
        Generate bills with no previous billing history and 3 previous sessions
        """
        start = NOW - datetime.timedelta(days=80, hours=2)
        end = NOW - datetime.timedelta(days=80, hours=1)
        start_month = start.replace(day=28, hour=23, minute=59, second=59)
        end_month = start.replace(day=28, hour=23, minute=59, second=59) + datetime.timedelta(days=4)
        models_a = self.bc.database.create(
            mentor_profile=1,
            user=1,
            mentorship_session={
                "status": "COMPLETED",
                "started_at": datetime.datetime(2021, 10, 16, 22, 0, tzinfo=pytz.UTC),
                "ended_at": datetime.datetime(2021, 10, 16, 23, 0, tzinfo=pytz.UTC),
                "accounted_duration": datetime.timedelta(hours=1),
            },
            mentorship_service=1,
            mentorship_bill={
                "status": "DUE",
                "started_at": start_month,
                "ended_at": end_month,
                "reviewer_id": None,
            },
        )
        models = self.bc.database.create(
            mentor_profile=models_a["mentor_profile"],
            user=models_a["user"],
            mentorship_service=1,
            mentorship_session=[
                {
                    "status": "COMPLETED",
                    "started_at": datetime.datetime(2021, 11, 16, 22, 0, tzinfo=pytz.UTC),
                    "ended_at": datetime.datetime(2021, 11, 16, 23, 0, tzinfo=pytz.UTC),
                    "accounted_duration": datetime.timedelta(hours=1),
                },
                {
                    "status": "COMPLETED",
                    "started_at": datetime.datetime(2021, 11, 17, 21, 0, tzinfo=pytz.UTC),
                    "ended_at": datetime.datetime(2021, 11, 17, 23, 0, tzinfo=pytz.UTC),
                    "accounted_duration": datetime.timedelta(hours=2),
                },
                {
                    "status": "COMPLETED",
                    "started_at": datetime.datetime(2021, 12, 30, 21, 0, tzinfo=pytz.UTC),
                    "ended_at": datetime.datetime(2021, 12, 30, 23, 0, tzinfo=pytz.UTC),
                    "accounted_duration": datetime.timedelta(hours=2),
                },
            ],
        )
        mentor = models.mentor_profile

        bills = generate_mentor_bills(mentor)
        list_bills = [self.bc.format.to_dict(x) for x in bills]

        bill1 = (
            round(models_a.mentorship_session.accounted_duration.seconds / 60 / 60, 2)
            * models.mentor_profile.price_per_hour
        )

        bill2 = (
            round(
                (
                    models.mentorship_session[0].accounted_duration.seconds
                    + models.mentorship_session[1].accounted_duration.seconds
                )
                / 60
                / 60,
                2,
            )
            * models.mentor_profile.price_per_hour
        )

        bill3 = (
            round((models.mentorship_session[2].accounted_duration.seconds) / 60 / 60, 2)
            * models.mentor_profile.price_per_hour
        )

        self.assertEqual(
            list_bills,
            [
                mentorship_bill_field(
                    {
                        "academy_id": 1,
                        "started_at": start_month,
                        "ended_at": end_month,
                        "id": 1,
                        "mentor_id": 1,
                        "overtime_minutes": 0,
                        "total_duration_in_hours": 1.0,
                        "total_duration_in_minutes": 60.0,
                        "total_price": bill1,
                        "reviewer_id": None,
                    }
                ),
                mentorship_bill_field(
                    {
                        "academy_id": 1,
                        "started_at": datetime.datetime(2021, 11, 1, 0, 0, 0, 0, tzinfo=pytz.UTC),
                        "ended_at": datetime.datetime(2021, 11, 30, 23, 59, 59, 999999, tzinfo=pytz.UTC),
                        "id": 2,
                        "mentor_id": 1,
                        "overtime_minutes": 60.0,
                        "total_duration_in_hours": 3.0,
                        "total_duration_in_minutes": 180.0,
                        "total_price": bill2,
                    }
                ),
                mentorship_bill_field(
                    {
                        "academy_id": 1,
                        "started_at": datetime.datetime(2021, 12, 1, 0, 0, 0, 0, tzinfo=pytz.UTC),
                        "ended_at": datetime.datetime(2021, 12, 31, 23, 59, 59, 999999, tzinfo=pytz.UTC),
                        "id": 3,
                        "mentor_id": 1,
                        "overtime_minutes": 60.0,
                        "total_duration_in_hours": 2.0,
                        "total_duration_in_minutes": 120.0,
                        "total_price": bill3,
                    }
                ),
            ],
        )

        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipBill"),
            [
                mentorship_bill_field(
                    {
                        "academy_id": 1,
                        "started_at": start_month,
                        "ended_at": end_month,
                        "id": 1,
                        "mentor_id": 1,
                        "overtime_minutes": 0.0,
                        "total_duration_in_hours": 1.0,
                        "total_duration_in_minutes": 60.0,
                        "total_price": bill1,
                        "reviewer_id": None,
                    }
                ),
                mentorship_bill_field(
                    {
                        "academy_id": 1,
                        "started_at": datetime.datetime(2021, 11, 1, 0, 0, 0, 0, tzinfo=pytz.UTC),
                        "ended_at": datetime.datetime(2021, 11, 30, 23, 59, 59, 999999, tzinfo=pytz.UTC),
                        "id": 2,
                        "mentor_id": 1,
                        "overtime_minutes": 60.0,
                        "total_duration_in_hours": 3.0,
                        "total_duration_in_minutes": 180.0,
                        "total_price": bill2,
                    }
                ),
                mentorship_bill_field(
                    {
                        "academy_id": 1,
                        "started_at": datetime.datetime(2021, 12, 1, 0, 0, 0, 0, tzinfo=pytz.UTC),
                        "ended_at": datetime.datetime(2021, 12, 31, 23, 59, 59, 999999, tzinfo=pytz.UTC),
                        "id": 3,
                        "mentor_id": 1,
                        "overtime_minutes": 60.0,
                        "total_duration_in_hours": 2.0,
                        "total_duration_in_minutes": 120.0,
                        "total_price": bill3,
                    }
                ),
            ],
        )

        status_message = "The mentor never joined the meeting, no time will be " "accounted for."

        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipSession"),
            [
                mentorship_session_field(
                    {
                        "accounted_duration": datetime.timedelta(seconds=3600),
                        "id": 1,
                        "mentee_id": 1,
                        "mentor_id": 1,
                        "service_id": 1,
                        "status": "COMPLETED",
                        "status_message": status_message,
                        "suggested_accounted_duration": datetime.timedelta(0),
                        "started_at": datetime.datetime(2021, 10, 16, 22, 0, tzinfo=pytz.UTC),
                        "ended_at": datetime.datetime(2021, 10, 16, 23, 0, tzinfo=pytz.UTC),
                        "summary": None,
                        "bill_id": 1,
                    }
                ),
                mentorship_session_field(
                    {
                        "accounted_duration": datetime.timedelta(seconds=3600),
                        "id": 2,
                        "mentee_id": 1,
                        "mentor_id": 1,
                        "service_id": 2,
                        "status": "COMPLETED",
                        "status_message": status_message,
                        "suggested_accounted_duration": datetime.timedelta(0),
                        "started_at": datetime.datetime(2021, 11, 16, 22, 0, tzinfo=pytz.UTC),
                        "ended_at": datetime.datetime(2021, 11, 16, 23, 0, tzinfo=pytz.UTC),
                        "summary": None,
                        "bill_id": 2,
                    }
                ),
                mentorship_session_field(
                    {
                        "accounted_duration": datetime.timedelta(seconds=7200),
                        "id": 3,
                        "mentee_id": 1,
                        "mentor_id": 1,
                        "service_id": 2,
                        "status": "COMPLETED",
                        "status_message": status_message,
                        "suggested_accounted_duration": datetime.timedelta(0),
                        "started_at": datetime.datetime(2021, 11, 17, 21, 0, tzinfo=pytz.UTC),
                        "ended_at": datetime.datetime(2021, 11, 17, 23, 0, tzinfo=pytz.UTC),
                        "summary": None,
                        "bill_id": 2,
                    }
                ),
                mentorship_session_field(
                    {
                        "accounted_duration": datetime.timedelta(seconds=7200),
                        "id": 4,
                        "mentee_id": 1,
                        "mentor_id": 1,
                        "service_id": 2,
                        "status": "COMPLETED",
                        "status_message": status_message,
                        "suggested_accounted_duration": datetime.timedelta(0),
                        "started_at": datetime.datetime(2021, 12, 30, 21, 0, tzinfo=pytz.UTC),
                        "ended_at": datetime.datetime(2021, 12, 30, 23, 0, tzinfo=pytz.UTC),
                        "summary": None,
                        "bill_id": 3,
                    }
                ),
            ],
        )

    @patch("django.utils.timezone.now", MagicMock(return_value=NOW))
    @patch("breathecode.notify.actions.send_email_message", MagicMock())
    def test_generate_bills_with_previous_bills_and_pending_sessions__status_recalculate(self):
        """
        Generate bills with no previous billing history and 3 previous sessions
        """
        start = NOW - datetime.timedelta(days=80, hours=2)
        end = NOW - datetime.timedelta(days=80, hours=1)
        start_month = start.replace(day=28, hour=23, minute=59, second=59)
        end_month = start.replace(day=28, hour=23, minute=59, second=59) + datetime.timedelta(days=4)
        models_a = self.bc.database.create(
            mentor_profile=1,
            user=1,
            mentorship_session={
                "status": "COMPLETED",
                "started_at": datetime.datetime(2021, 10, 16, 22, 0, tzinfo=pytz.UTC),
                "ended_at": datetime.datetime(2021, 10, 16, 23, 0, tzinfo=pytz.UTC),
                "accounted_duration": datetime.timedelta(hours=1),
            },
            mentorship_service=1,
            mentorship_bill={
                "status": "RECALCULATE",
                "started_at": start_month,
                "ended_at": end_month,
                "reviewer_id": None,
            },
        )
        models = self.bc.database.create(
            mentor_profile=models_a["mentor_profile"],
            user=models_a["user"],
            mentorship_service=1,
            mentorship_session=[
                {
                    "status": "COMPLETED",
                    "started_at": datetime.datetime(2021, 11, 16, 22, 0, tzinfo=pytz.UTC),
                    "ended_at": datetime.datetime(2021, 11, 16, 23, 0, tzinfo=pytz.UTC),
                    "accounted_duration": datetime.timedelta(hours=1),
                },
                {
                    "status": "COMPLETED",
                    "started_at": datetime.datetime(2021, 11, 17, 21, 0, tzinfo=pytz.UTC),
                    "ended_at": datetime.datetime(2021, 11, 17, 23, 0, tzinfo=pytz.UTC),
                    "accounted_duration": datetime.timedelta(hours=2),
                },
                {
                    "status": "COMPLETED",
                    "started_at": datetime.datetime(2021, 12, 30, 21, 0, tzinfo=pytz.UTC),
                    "ended_at": datetime.datetime(2021, 12, 30, 23, 0, tzinfo=pytz.UTC),
                    "accounted_duration": datetime.timedelta(hours=2),
                },
            ],
        )
        mentor = models.mentor_profile

        bills = generate_mentor_bills(mentor)
        list_bills = [self.bc.format.to_dict(x) for x in bills]

        bill1 = (
            round(models_a.mentorship_session.accounted_duration.seconds / 60 / 60, 2)
            * models.mentor_profile.price_per_hour
        )

        bill2 = (
            round(
                (
                    models.mentorship_session[0].accounted_duration.seconds
                    + models.mentorship_session[1].accounted_duration.seconds
                )
                / 60
                / 60,
                2,
            )
            * models.mentor_profile.price_per_hour
        )

        bill3 = (
            round((models.mentorship_session[2].accounted_duration.seconds) / 60 / 60, 2)
            * models.mentor_profile.price_per_hour
        )

        self.assertEqual(
            list_bills,
            [
                mentorship_bill_field(
                    {
                        "academy_id": 1,
                        "started_at": start_month,
                        "ended_at": end_month,
                        "id": 1,
                        "mentor_id": 1,
                        "overtime_minutes": 0,
                        "total_duration_in_hours": 1.0,
                        "total_duration_in_minutes": 60.0,
                        "total_price": bill1,
                    }
                ),
                mentorship_bill_field(
                    {
                        "academy_id": 1,
                        "started_at": datetime.datetime(2021, 11, 1, 0, 0, 0, 0, tzinfo=pytz.UTC),
                        "ended_at": datetime.datetime(2021, 11, 30, 23, 59, 59, 999999, tzinfo=pytz.UTC),
                        "id": 2,
                        "mentor_id": 1,
                        "overtime_minutes": 60.0,
                        "total_duration_in_hours": 3.0,
                        "total_duration_in_minutes": 180.0,
                        "total_price": bill2,
                    }
                ),
                mentorship_bill_field(
                    {
                        "academy_id": 1,
                        "started_at": datetime.datetime(2021, 12, 1, 0, 0, 0, 0, tzinfo=pytz.UTC),
                        "ended_at": datetime.datetime(2021, 12, 31, 23, 59, 59, 999999, tzinfo=pytz.UTC),
                        "id": 3,
                        "mentor_id": 1,
                        "overtime_minutes": 60.0,
                        "total_duration_in_hours": 2.0,
                        "total_duration_in_minutes": 120.0,
                        "total_price": bill3,
                    }
                ),
            ],
        )

        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipBill"),
            [
                mentorship_bill_field(
                    {
                        "academy_id": 1,
                        "started_at": start_month,
                        "ended_at": end_month,
                        "id": 1,
                        "mentor_id": 1,
                        "overtime_minutes": 0.0,
                        "total_duration_in_hours": 1.0,
                        "total_duration_in_minutes": 60.0,
                        "total_price": bill1,
                    }
                ),
                mentorship_bill_field(
                    {
                        "academy_id": 1,
                        "started_at": datetime.datetime(2021, 11, 1, 0, 0, 0, 0, tzinfo=pytz.UTC),
                        "ended_at": datetime.datetime(2021, 11, 30, 23, 59, 59, 999999, tzinfo=pytz.UTC),
                        "id": 2,
                        "mentor_id": 1,
                        "overtime_minutes": 60.0,
                        "total_duration_in_hours": 3.0,
                        "total_duration_in_minutes": 180.0,
                        "total_price": bill2,
                    }
                ),
                mentorship_bill_field(
                    {
                        "academy_id": 1,
                        "started_at": datetime.datetime(2021, 12, 1, 0, 0, 0, 0, tzinfo=pytz.UTC),
                        "ended_at": datetime.datetime(2021, 12, 31, 23, 59, 59, 999999, tzinfo=pytz.UTC),
                        "id": 3,
                        "mentor_id": 1,
                        "overtime_minutes": 60.0,
                        "total_duration_in_hours": 2.0,
                        "total_duration_in_minutes": 120.0,
                        "total_price": bill3,
                    }
                ),
            ],
        )

        status_message = "The mentor never joined the meeting, no time will be " "accounted for."

        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipSession"),
            [
                mentorship_session_field(
                    {
                        "accounted_duration": datetime.timedelta(seconds=3600),
                        "id": 1,
                        "mentee_id": 1,
                        "mentor_id": 1,
                        "service_id": 1,
                        "status": "COMPLETED",
                        "status_message": status_message,
                        "suggested_accounted_duration": datetime.timedelta(0),
                        "started_at": datetime.datetime(2021, 10, 16, 22, 0, tzinfo=pytz.UTC),
                        "ended_at": datetime.datetime(2021, 10, 16, 23, 0, tzinfo=pytz.UTC),
                        "summary": None,
                        "bill_id": 1,
                    }
                ),
                mentorship_session_field(
                    {
                        "accounted_duration": datetime.timedelta(seconds=3600),
                        "id": 2,
                        "mentee_id": 1,
                        "mentor_id": 1,
                        "service_id": 2,
                        "status": "COMPLETED",
                        "status_message": status_message,
                        "suggested_accounted_duration": datetime.timedelta(0),
                        "started_at": datetime.datetime(2021, 11, 16, 22, 0, tzinfo=pytz.UTC),
                        "ended_at": datetime.datetime(2021, 11, 16, 23, 0, tzinfo=pytz.UTC),
                        "summary": None,
                        "bill_id": 2,
                    }
                ),
                mentorship_session_field(
                    {
                        "accounted_duration": datetime.timedelta(seconds=7200),
                        "id": 3,
                        "mentee_id": 1,
                        "mentor_id": 1,
                        "service_id": 2,
                        "status": "COMPLETED",
                        "status_message": status_message,
                        "suggested_accounted_duration": datetime.timedelta(0),
                        "started_at": datetime.datetime(2021, 11, 17, 21, 0, tzinfo=pytz.UTC),
                        "ended_at": datetime.datetime(2021, 11, 17, 23, 0, tzinfo=pytz.UTC),
                        "summary": None,
                        "bill_id": 2,
                    }
                ),
                mentorship_session_field(
                    {
                        "accounted_duration": datetime.timedelta(seconds=7200),
                        "id": 4,
                        "mentee_id": 1,
                        "mentor_id": 1,
                        "service_id": 2,
                        "status": "COMPLETED",
                        "status_message": status_message,
                        "suggested_accounted_duration": datetime.timedelta(0),
                        "started_at": datetime.datetime(2021, 12, 30, 21, 0, tzinfo=pytz.UTC),
                        "ended_at": datetime.datetime(2021, 12, 30, 23, 0, tzinfo=pytz.UTC),
                        "summary": None,
                        "bill_id": 3,
                    }
                ),
            ],
        )
