"""
This file just can contains duck tests refert to AcademyInviteView
"""

import random
from datetime import timedelta
from unittest.mock import MagicMock, call, patch

from django.urls.base import reverse_lazy
from django.utils import timezone
from rest_framework import status

from breathecode.mentorship import signals
from breathecode.utils.api_view_extensions.api_view_extension_handlers import APIViewExtensionHandlers

from ..mixins import MentorshipTestCase

UTC_NOW = timezone.now()


def format_datetime(self, date):
    if date is None:
        return None

    return self.bc.datetime.to_iso_string(date)


def get_serializer(self, mentorship_session, mentor_profile, mentorship_service, user, academy, data={}):
    return {
        "accounted_duration": mentorship_session.accounted_duration,
        "allow_billing": mentorship_session.allow_billing,
        "ended_at": format_datetime(self, mentorship_session.ended_at),
        "id": mentorship_session.id,
        "bill": (
            mentorship_session.bill
            if mentorship_session.bill is None
            else {"id": mentorship_session.bill.id, "status": mentorship_session.bill.status}
        ),
        "mentee": {
            "email": user.email,
            "first_name": user.first_name,
            "id": user.id,
            "last_name": user.last_name,
        },
        "mentee_left_at": mentorship_session.mentee_left_at,
        "mentor": {
            "booking_url": mentor_profile.booking_url,
            "id": mentor_profile.id,
            "services": [
                {
                    "academy": {
                        "icon_url": academy.icon_url,
                        "id": academy.id,
                        "logo_url": academy.logo_url,
                        "name": academy.name,
                        "slug": academy.slug,
                    },
                    "allow_mentee_to_extend": mentorship_service.allow_mentee_to_extend,
                    "allow_mentors_to_extend": mentorship_service.allow_mentors_to_extend,
                    "duration": self.bc.datetime.from_timedelta(mentorship_service.duration),
                    "created_at": self.bc.datetime.to_iso_string(mentorship_service.created_at),
                    "id": mentorship_service.id,
                    "language": mentorship_service.language,
                    "logo_url": mentorship_service.logo_url,
                    "max_duration": self.bc.datetime.from_timedelta(mentorship_service.max_duration),
                    "missed_meeting_duration": self.bc.datetime.from_timedelta(
                        mentorship_service.missed_meeting_duration
                    ),
                    "name": mentorship_service.name,
                    "slug": mentorship_service.slug,
                    "status": mentorship_service.status,
                    "updated_at": self.bc.datetime.to_iso_string(mentorship_service.updated_at),
                }
            ],
            "slug": mentor_profile.slug,
            "status": mentor_profile.status,
            "user": {
                "email": user.email,
                "first_name": user.first_name,
                "id": user.id,
                "last_name": user.last_name,
            },
        },
        "mentor_joined_at": mentorship_session.mentor_joined_at,
        "mentor_left_at": mentorship_session.mentor_left_at,
        "service": {
            "id": mentorship_service.id,
            "name": mentorship_service.name,
            "slug": mentorship_service.slug,
            "duration": str(mentorship_service.duration.total_seconds()),
        },
        "started_at": format_datetime(self, mentorship_session.started_at),
        "status": mentorship_session.status,
        "summary": mentorship_session.summary,
        "rating": None,
        **data,
    }


def post_serializer(data={}):
    return {
        "accounted_duration": None,
        "agenda": None,
        "allow_billing": False,
        "bill": None,
        "ended_at": None,
        "ends_at": None,
        "id": 1,
        "is_online": False,
        "latitude": None,
        "longitude": None,
        "mentee": None,
        "mentee_left_at": None,
        "mentor": 1,
        "service": None,
        "mentor_joined_at": None,
        "mentor_left_at": None,
        "name": None,
        "online_meeting_url": None,
        "online_recording_url": None,
        "started_at": None,
        "starts_at": None,
        "status": "PENDING",
        "summary": None,
        **data,
    }


def put_serializer(data={}):
    return {
        "accounted_duration": None,
        "agenda": None,
        "allow_billing": True,
        "bill": None,
        "ended_at": None,
        "ends_at": None,
        "calendly_uuid": None,
        "id": 0,
        "is_online": False,
        "latitude": None,
        "longitude": None,
        "mentee": 0,
        "mentee_left_at": None,
        "mentor": 0,
        "mentor_joined_at": None,
        "mentor_left_at": None,
        "name": None,
        "online_meeting_url": None,
        "online_recording_url": None,
        "service": 0,
        "started_at": None,
        "starts_at": None,
        "status": "PENDING",
        "summary": None,
        "questions_and_answers": None,
        **data,
    }


def mentorship_session_columns(data={}):
    return {
        "accounted_duration": None,
        "agenda": None,
        "allow_billing": False,
        "bill_id": None,
        "ended_at": None,
        "calendly_uuid": None,
        "ends_at": None,
        "id": 1,
        "is_online": False,
        "latitude": None,
        "longitude": None,
        "mentee_id": None,
        "service_id": None,
        "mentee_left_at": None,
        "mentor_id": 1,
        "mentor_joined_at": None,
        "mentor_left_at": None,
        "name": None,
        "online_meeting_url": None,
        "online_recording_url": None,
        "started_at": None,
        "starts_at": None,
        "status": "PENDING",
        "status_message": None,
        "suggested_accounted_duration": None,
        "summary": None,
        "questions_and_answers": None,
        **data,
    }


def get_base_number() -> int:
    return 1 if random.random() < 0.5 else -1


def append_delta_to_datetime(date):
    return date + timedelta(minutes=random.randint(0, 180))


class AcademyServiceTestSuite(MentorshipTestCase):
    """
    🔽🔽🔽 Auth
    """

    def test__get__without_auth(self):
        url = reverse_lazy("mentorship:academy_session")
        response = self.client.get(url)

        json = response.json()
        expected = {
            "detail": "Authentication credentials were not provided.",
            "status_code": status.HTTP_401_UNAUTHORIZED,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test__get__without_academy_header(self):
        model = self.bc.database.create(user=1)

        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_session")
        response = self.client.get(url)

        json = response.json()
        expected = {
            "detail": "Missing academy_id parameter expected for the endpoint url or 'Academy' header",
            "status_code": 403,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    """
    🔽🔽🔽 GET capability
    """

    def test__get__without_capabilities(self):
        model = self.bc.database.create(user=1)

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_session")
        response = self.client.get(url)

        json = response.json()
        expected = {
            "detail": "You (user: 1) don't have this capability: read_mentorship_session for academy 1",
            "status_code": 403,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    """
    🔽🔽🔽 GET without data
    """

    def test__get__without_data(self):
        model = self.bc.database.create(user=1, role=1, capability="read_mentorship_session", profile_academy=1)

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_session")
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    """
    🔽🔽🔽 GET with one MentorshipSession, MentorProfile and MentorshipService
    """

    def test__get__with_one_mentor_profile(self):
        model = self.bc.database.create(
            user=1,
            role=1,
            capability="read_mentorship_session",
            mentorship_session=1,
            mentor_profile=1,
            mentorship_service=1,
            profile_academy=1,
        )

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_session")
        response = self.client.get(url)

        json = response.json()
        expected = [
            get_serializer(
                self,
                model.mentorship_session,
                model.mentor_profile,
                model.mentorship_service,
                model.user,
                model.academy,
                data={},
            ),
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipSession"),
            [
                self.bc.format.to_dict(model.mentorship_session),
            ],
        )

    """
    🔽🔽🔽 GET with two MentorshipSession, one MentorProfile and one MentorshipService
    """

    def test__get__with_two_mentor_profile(self):
        model = self.bc.database.create(
            user=1,
            role=1,
            capability="read_mentorship_session",
            mentorship_session=2,
            mentor_profile=1,
            mentorship_service=1,
            profile_academy=1,
        )

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_session")
        response = self.client.get(url)

        json = response.json()
        mentorship_session_list = sorted(model.mentorship_session, key=lambda x: x.created_at, reverse=True)
        expected = [
            get_serializer(
                self,
                mentorship_session,
                model.mentor_profile,
                model.mentorship_service,
                model.user,
                model.academy,
                data={},
            )
            for mentorship_session in mentorship_session_list
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipSession"),
            self.bc.format.to_dict(model.mentorship_session),
        )

    """
    🔽🔽🔽 GET with two MentorshipSession, one MentorProfile and one MentorshipService, passing status
    """

    def test__get__with_two_mentor_profile__passing_bad_status(self):
        statuses = ["PENDING", "STARTED", "COMPLETED", "FAILED", "IGNORED"]

        for n in range(0, 4):
            first_status = statuses[n]
            second_status = statuses[n + 1]

            choices = [first_status, second_status]
            mentorship_sessions = [{"status": x} for x in choices]
            bad_statuses = ",".join([x for x in statuses if x not in choices])
            model = self.bc.database.create(
                user=1,
                role=1,
                capability="read_mentorship_session",
                mentorship_session=mentorship_sessions,
                mentor_profile=1,
                mentorship_service=1,
                profile_academy=1,
            )

            self.bc.request.set_headers(academy=model.academy.id)
            self.client.force_authenticate(model.user)

            url = reverse_lazy("mentorship:academy_session") + f"?status={bad_statuses}"
            response = self.client.get(url)

            json = response.json()
            expected = []

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(
                self.bc.database.list_of("mentorship.MentorshipSession"),
                self.bc.format.to_dict(model.mentorship_session),
            )

            # teardown
            self.bc.database.delete("mentorship.MentorshipSession")

    def test__get__with_two_mentor_profile__passing_status(self):
        statuses = ["PENDING", "STARTED", "COMPLETED", "FAILED", "IGNORED"]

        for n in range(0, 4):
            first_status = statuses[n]
            second_status = statuses[n + 1]

            choices = [first_status, second_status]
            mentorship_sessions = [{"status": x} for x in choices]
            model = self.bc.database.create(
                user=1,
                role=1,
                capability="read_mentorship_session",
                mentorship_session=mentorship_sessions,
                mentor_profile=1,
                mentorship_service=1,
                profile_academy=1,
            )

            self.bc.request.set_headers(academy=model.academy.id)
            self.client.force_authenticate(model.user)

            url = reverse_lazy("mentorship:academy_session") + f"?status={first_status},{second_status}"
            response = self.client.get(url)

            json = response.json()
            mentorship_session_list = sorted(model.mentorship_session, key=lambda x: x.created_at, reverse=True)
            expected = [
                get_serializer(
                    self,
                    mentorship_session_list[0],
                    model.mentor_profile,
                    model.mentorship_service,
                    model.user,
                    model.academy,
                    data={"status": second_status},
                ),
                get_serializer(
                    self,
                    mentorship_session_list[1],
                    model.mentor_profile,
                    model.mentorship_service,
                    model.user,
                    model.academy,
                    data={"status": first_status},
                ),
            ]

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(
                self.bc.database.list_of("mentorship.MentorshipSession"),
                self.bc.format.to_dict(model.mentorship_session),
            )

            # teardown
            self.bc.database.delete("mentorship.MentorshipSession")

    """
    🔽🔽🔽 GET with two MentorshipSession, one MentorProfile and one MentorshipService, passing billed
    """

    def test__get__with_two_mentor_profile__passing_billed_as_true__without_mentorship_bill(self):
        model = self.bc.database.create(
            user=1,
            role=1,
            capability="read_mentorship_session",
            mentorship_session=1,
            mentor_profile=1,
            mentorship_service=1,
            profile_academy=1,
        )

        self.bc.request.set_headers(academy=model.academy.id)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_session") + f"?billed=true"
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipSession"),
            [
                self.bc.format.to_dict(model.mentorship_session),
            ],
        )

    def test__get__with_two_mentor_profile__passing_billed_as_true__with_mentorship_bill(self):
        model = self.bc.database.create(
            user=1,
            role=1,
            capability="read_mentorship_session",
            mentorship_session=1,
            mentor_profile=1,
            mentorship_bill=1,
            mentorship_service=1,
            profile_academy=1,
        )

        self.bc.request.set_headers(academy=model.academy.id)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_session") + f"?billed=true"
        response = self.client.get(url)

        json = response.json()
        expected = [
            get_serializer(
                self,
                model.mentorship_session,
                model.mentor_profile,
                model.mentorship_service,
                model.user,
                model.academy,
                data={},
            ),
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipSession"),
            [
                self.bc.format.to_dict(model.mentorship_session),
            ],
        )

    def test__get__with_two_mentor_profile__passing_billed_as_false__with_mentorship_bill(self):
        model = self.bc.database.create(
            user=1,
            role=1,
            capability="read_mentorship_session",
            mentorship_session=1,
            mentor_profile=1,
            mentorship_bill=1,
            mentorship_service=1,
            profile_academy=1,
        )

        self.bc.request.set_headers(academy=model.academy.id)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_session") + f"?billed=false"
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipSession"),
            [
                self.bc.format.to_dict(model.mentorship_session),
            ],
        )

    def test__get__with_two_mentor_profile__passing_billed_as_false__without_mentorship_bill(self):
        model = self.bc.database.create(
            user=1,
            role=1,
            capability="read_mentorship_session",
            mentorship_session=1,
            mentor_profile=1,
            mentorship_service=1,
            profile_academy=1,
        )

        self.bc.request.set_headers(academy=model.academy.id)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_session") + f"?billed=false"
        response = self.client.get(url)

        json = response.json()
        expected = [
            get_serializer(
                self,
                model.mentorship_session,
                model.mentor_profile,
                model.mentorship_service,
                model.user,
                model.academy,
                data={},
            ),
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipSession"),
            [
                self.bc.format.to_dict(model.mentorship_session),
            ],
        )

    """
    🔽🔽🔽 GET with two MentorshipSession, one MentorProfile and one MentorshipService, passing started_after
    """

    def test__get__with_two_mentor_profile__passing_bad_started_after(self):
        utc_now = timezone.now()
        mentorship_session = {"started_at": utc_now}
        model = self.bc.database.create(
            user=1,
            role=1,
            capability="read_mentorship_session",
            mentorship_session=mentorship_session,
            mentor_profile=1,
            mentorship_service=1,
            profile_academy=1,
        )

        self.bc.request.set_headers(academy=model.academy.id)
        self.client.force_authenticate(model.user)

        url = (
            reverse_lazy("mentorship:academy_session")
            + f"?started_after={self.bc.datetime.to_iso_string(utc_now + timedelta(seconds=1))}"
        )
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipSession"),
            [
                self.bc.format.to_dict(model.mentorship_session),
            ],
        )

    def test__get__with_two_mentor_profile__passing_started_after(self):
        utc_now = timezone.now()
        mentorship_session = {"started_at": utc_now}
        model = self.bc.database.create(
            user=1,
            role=1,
            capability="read_mentorship_session",
            mentorship_session=mentorship_session,
            mentor_profile=1,
            mentorship_service=1,
            profile_academy=1,
        )

        self.bc.request.set_headers(academy=model.academy.id)
        self.client.force_authenticate(model.user)

        url = (
            reverse_lazy("mentorship:academy_session")
            + f"?started_after={self.bc.datetime.to_iso_string(utc_now - timedelta(seconds=1))}"
        )
        response = self.client.get(url)

        json = response.json()
        expected = [
            get_serializer(
                self,
                model.mentorship_session,
                model.mentor_profile,
                model.mentorship_service,
                model.user,
                model.academy,
                data={},
            ),
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipSession"),
            [
                self.bc.format.to_dict(model.mentorship_session),
            ],
        )

    def test__get__with_two_mentor_profile__passing_started_after__without_started_at(self):
        utc_now = timezone.now()
        model = self.bc.database.create(
            user=1,
            role=1,
            capability="read_mentorship_session",
            mentorship_session=1,
            mentor_profile=1,
            mentorship_service=1,
            profile_academy=1,
        )

        self.bc.request.set_headers(academy=model.academy.id)
        self.client.force_authenticate(model.user)

        cases = [
            self.bc.datetime.to_iso_string(utc_now - timedelta(seconds=1)),
            self.bc.datetime.to_iso_string(utc_now + timedelta(seconds=1)),
        ]
        for case in cases:
            url = reverse_lazy("mentorship:academy_session") + f"?started_after={case}"
            response = self.client.get(url)

            json = response.json()
            expected = [
                get_serializer(
                    self,
                    model.mentorship_session,
                    model.mentor_profile,
                    model.mentorship_service,
                    model.user,
                    model.academy,
                    data={},
                ),
            ]

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(
                self.bc.database.list_of("mentorship.MentorshipSession"),
                [
                    self.bc.format.to_dict(model.mentorship_session),
                ],
            )

    """
    🔽🔽🔽 GET with two MentorshipSession, one MentorProfile and one MentorshipService, passing ended_before
    """

    def test__get__with_two_mentor_profile__passing_bad_ended_before(self):
        utc_now = timezone.now()
        mentorship_session = {"ended_at": utc_now}
        model = self.bc.database.create(
            user=1,
            role=1,
            capability="read_mentorship_session",
            mentorship_session=mentorship_session,
            mentor_profile=1,
            mentorship_service=1,
            profile_academy=1,
        )

        self.bc.request.set_headers(academy=model.academy.id)
        self.client.force_authenticate(model.user)

        url = (
            reverse_lazy("mentorship:academy_session")
            + f"?ended_before={self.bc.datetime.to_iso_string(utc_now - timedelta(seconds=1))}"
        )
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipSession"),
            [
                self.bc.format.to_dict(model.mentorship_session),
            ],
        )

    def test__get__with_two_mentor_profile__passing_ended_before(self):
        utc_now = timezone.now()
        mentorship_session = {"ended_at": utc_now}
        model = self.bc.database.create(
            user=1,
            role=1,
            capability="read_mentorship_session",
            mentorship_session=mentorship_session,
            mentor_profile=1,
            mentorship_service=1,
            profile_academy=1,
        )

        self.bc.request.set_headers(academy=model.academy.id)
        self.client.force_authenticate(model.user)

        url = (
            reverse_lazy("mentorship:academy_session")
            + f"?ended_before={self.bc.datetime.to_iso_string(utc_now + timedelta(seconds=1))}"
        )
        response = self.client.get(url)

        json = response.json()
        expected = [
            get_serializer(
                self,
                model.mentorship_session,
                model.mentor_profile,
                model.mentorship_service,
                model.user,
                model.academy,
                data={},
            ),
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipSession"),
            [
                self.bc.format.to_dict(model.mentorship_session),
            ],
        )

    def test__get__with_two_mentor_profile__passing_ended_before__without_ended_at(self):
        utc_now = timezone.now()
        model = self.bc.database.create(
            user=1,
            role=1,
            capability="read_mentorship_session",
            mentorship_session=1,
            mentor_profile=1,
            mentorship_service=1,
            profile_academy=1,
        )

        self.bc.request.set_headers(academy=model.academy.id)
        self.client.force_authenticate(model.user)

        cases = [
            self.bc.datetime.to_iso_string(utc_now - timedelta(seconds=1)),
            self.bc.datetime.to_iso_string(utc_now + timedelta(seconds=1)),
        ]

        for case in cases:
            url = reverse_lazy("mentorship:academy_session") + f"?ended_before={case}"
            response = self.client.get(url)

            json = response.json()
            expected = [
                get_serializer(
                    self,
                    model.mentorship_session,
                    model.mentor_profile,
                    model.mentorship_service,
                    model.user,
                    model.academy,
                    data={},
                ),
            ]

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(
                self.bc.database.list_of("mentorship.MentorshipSession"),
                [
                    self.bc.format.to_dict(model.mentorship_session),
                ],
            )

    """
    🔽🔽🔽 GET with four MentorshipSession, MentorProfile and MentorshipService, passing mentor
    """

    def test__get__with_four_elements__padding_bad_mentor(self):
        mentorship_sessions = [{"mentee_id": x, "mentor_id": x} for x in range(1, 5)]
        mentor_profiles = [{"user_id": x, "services": [x]} for x in range(1, 5)]
        model = self.bc.database.create(
            user=4,
            role=1,
            capability="read_mentorship_session",
            mentorship_session=mentorship_sessions,
            mentor_profile=mentor_profiles,
            mentorship_service=4,
            profile_academy=1,
        )

        self.bc.request.set_headers(academy=1)
        self.bc.request.authenticate(model.user[0])

        url = reverse_lazy("mentorship:academy_session") + f"?mentor=5,6"
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipSession"),
            self.bc.format.to_dict(model.mentorship_session),
        )

    def test__get__with_four_elements__padding_mentor(self):
        mentorship_sessions = [{"mentee_id": x, "mentor_id": x, "service_id": x} for x in range(1, 5)]
        mentor_profiles = [{"user_id": x, "services": [x]} for x in range(1, 5)]
        model = self.bc.database.create(
            user=4,
            role=1,
            capability="read_mentorship_session",
            mentorship_session=mentorship_sessions,
            mentor_profile=mentor_profiles,
            mentorship_service=4,
            profile_academy=1,
        )

        self.bc.request.set_headers(academy=1)
        self.bc.request.authenticate(model.user[0])

        url = reverse_lazy("mentorship:academy_session") + f"?mentor=1,3"
        response = self.client.get(url)

        json = response.json()
        expected = [
            get_serializer(
                self,
                model.mentorship_session[2],
                model.mentor_profile[2],
                model.mentorship_service[2],
                model.user[2],
                model.academy,
                data={},
            ),
            get_serializer(
                self,
                model.mentorship_session[0],
                model.mentor_profile[0],
                model.mentorship_service[0],
                model.user[0],
                model.academy,
                data={},
            ),
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipSession"),
            self.bc.format.to_dict(model.mentorship_session),
        )

    """
    🔽🔽🔽 Spy the extensions
    """

    @patch.object(APIViewExtensionHandlers, "_spy_extensions", MagicMock())
    @patch.object(APIViewExtensionHandlers, "_spy_extension_arguments", MagicMock())
    def test__get__spy_extensions(self):
        model = self.bc.database.create(
            user=1, role=1, capability="read_mentorship_session", mentorship_session=1, profile_academy=1
        )

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_session")
        self.client.get(url)

        self.assertEqual(
            APIViewExtensionHandlers._spy_extensions.call_args_list,
            [
                call(["LanguageExtension", "LookupExtension", "PaginationExtension", "SortExtension"]),
            ],
        )

        self.assertEqual(
            APIViewExtensionHandlers._spy_extension_arguments.call_args_list,
            [
                call(sort="-created_at", paginate=True),
            ],
        )

    """
    🔽🔽🔽 POST capability
    """

    def test__post__without_capabilities(self):
        model = self.bc.database.create(user=1)

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_session")
        response = self.client.post(url)

        json = response.json()
        expected = {
            "detail": "You (user: 1) don't have this capability: crud_mentorship_session for academy 1",
            "status_code": 403,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    """
    🔽🔽🔽 POST with one MentorshipSession, MentorProfile and MentorshipService
    """

    def test__post__missing_fields(self):
        model = self.bc.database.create(user=1, role=1, capability="crud_mentorship_session", profile_academy=1)

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_session")
        response = self.client.post(url)

        json = response.json()
        expected = {"mentor": ["This field is required."], "service": ["This field is required."]}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of("mentorship.MentorshipSession"), [])

    """
    🔽🔽🔽 POST creating a element
    """

    def test__post__creating_a_element(self):
        model = self.bc.database.create(
            user=1,
            role=1,
            capability="crud_mentorship_session",
            mentor_profile=1,
            mentorship_service=1,
            profile_academy=1,
        )

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_session")
        data = {"mentor": 1, "service": 1}
        response = self.client.post(url, data)

        json = response.json()
        expected = post_serializer(
            {
                "allow_billing": False,
                "service": {
                    "id": model.mentorship_service.id,
                    "name": model.mentorship_service.name,
                    "slug": model.mentorship_service.slug,
                },
                "mentor": {
                    "id": model.mentor_profile.id,
                    "slug": model.mentor_profile.slug,
                    "status": model.mentor_profile.status,
                    "user": {
                        "first_name": model.mentor_profile.user.first_name,
                        "last_name": model.mentor_profile.user.last_name,
                        "email": model.mentor_profile.user.email,
                        "id": model.mentor_profile.user.id,
                    },
                },
            }
        )

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipSession"),
            [
                mentorship_session_columns(
                    {
                        "allow_billing": False,
                        "service_id": 1,
                    }
                ),
            ],
        )

    """
    🔽🔽🔽 POST creating a element, passing the forbidden fields
    """

    def test__post__creating_a_element__passing_the_forbidden_fields(self):
        utc_now = timezone.now()
        model = self.bc.database.create(
            user=1,
            role=1,
            capability="crud_mentorship_session",
            mentor_profile=1,
            mentorship_service=1,
            profile_academy=1,
        )

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        data = {
            "mentor": 1,
            "service": 1,
            # readonly fields
            "created_at": utc_now,
            "updated_at": utc_now,
            "suggested_accounted_duration": "20",
            "status_message": "101010101010101010101",
        }

        url = reverse_lazy("mentorship:academy_session")
        response = self.client.post(url, data)

        json = response.json()
        expected = post_serializer(
            {
                "allow_billing": False,
                "service": {
                    "id": model.mentorship_service.id,
                    "name": model.mentorship_service.name,
                    "slug": model.mentorship_service.slug,
                },
                "mentor": {
                    "id": model.mentor_profile.id,
                    "slug": model.mentor_profile.slug,
                    "status": model.mentor_profile.status,
                    "user": {
                        "first_name": model.mentor_profile.user.first_name,
                        "last_name": model.mentor_profile.user.last_name,
                        "email": model.mentor_profile.user.email,
                        "id": model.mentor_profile.user.id,
                    },
                },
            }
        )

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipSession"),
            [
                mentorship_session_columns(
                    {
                        "allow_billing": False,
                        "service_id": 1,
                    }
                ),
            ],
        )

    """
    🔽🔽🔽 POST creating a element, passing readonly fields
    """

    def test__post__creating_a_element__passing_readonly_fields__is_online_as_true(self):
        utc_now = timezone.now()
        model = self.bc.database.create(
            user=1,
            role=1,
            capability="crud_mentorship_session",
            mentor_profile=1,
            mentorship_service=1,
            profile_academy=1,
        )

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        fields = ["mentor_joined_at", "mentor_left_at", "mentee_left_at", "started_at", "ended_at"]
        for field in fields:
            data = {
                "mentor": 1,
                "service": 1,
                "is_online": True,
                # readonly fields
                field: self.bc.datetime.to_iso_string(append_delta_to_datetime(utc_now)),
            }

            url = reverse_lazy("mentorship:academy_session")
            response = self.client.post(url, data)

            json = response.json()
            expected = {"detail": "read-only-field-online", "status_code": 400}

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(self.bc.database.list_of("mentorship.MentorshipSession"), [])

    def test__post__creating_a_element__passing_readonly_fields__is_online_as_false(self):
        utc_now = timezone.now()
        model = self.bc.database.create(
            user=1,
            role=1,
            capability="crud_mentorship_session",
            mentor_profile=1,
            mentorship_service=1,
            profile_academy=1,
        )

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        fields = ["mentor_joined_at", "mentor_left_at", "mentee_left_at", "started_at", "ended_at"]
        id = 0
        for field in fields:
            id += 1
            date = append_delta_to_datetime(utc_now)
            data = {
                "mentor": 1,
                "service": 1,
                "is_online": False,
                # readonly fields
                field: self.bc.datetime.to_iso_string(date),
            }

            url = reverse_lazy("mentorship:academy_session")
            response = self.client.post(url, data)

            json = response.json()
            expected = post_serializer(
                {
                    "allow_billing": False,
                    "id": id,
                    "service": {
                        "id": model.mentorship_service.id,
                        "name": model.mentorship_service.name,
                        "slug": model.mentorship_service.slug,
                    },
                    "mentor": {
                        "id": model.mentor_profile.id,
                        "slug": model.mentor_profile.slug,
                        "status": model.mentor_profile.status,
                        "user": {
                            "first_name": model.mentor_profile.user.first_name,
                            "last_name": model.mentor_profile.user.last_name,
                            "email": model.mentor_profile.user.email,
                            "id": model.mentor_profile.user.id,
                        },
                    },
                    field: self.bc.datetime.to_iso_string(date),
                }
            )

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertEqual(
                self.bc.database.list_of("mentorship.MentorshipSession"),
                [
                    mentorship_session_columns(
                        {
                            "allow_billing": False,
                            "id": id,
                            "service_id": 1,
                            field: date,
                        }
                    ),
                ],
            )

            # teardown
            self.bc.database.delete("mentorship.MentorshipSession")

    """
    🔽🔽🔽 POST creating a element, no cohort user
    """

    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock())
    def test__post__creating_a_element__no_cohort_user(self):
        utc_now = timezone.now()
        model = self.bc.database.create(
            user=1,
            role=1,
            capability="crud_mentorship_session",
            mentor_profile=1,
            mentorship_bill=1,
            mentorship_service=1,
            profile_academy=1,
        )

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        accounted_duration = timedelta(minutes=random.randint(1, 180))
        starts_at = append_delta_to_datetime(utc_now)
        ends_at = append_delta_to_datetime(utc_now)
        data = {
            "mentor": 1,
            "service": 1,
            "mentee": 1,
            "bill": 1,
            "name": self.bc.fake.name(),
            "is_online": bool(random.getrandbits(1)),
            "latitude": get_base_number() * random.random() * 1000,
            "longitude": get_base_number() * random.random() * 1000,
            "online_meeting_url": self.bc.fake.url(),
            "online_recording_url": self.bc.fake.url(),
            "status": random.choice(["PENDING", "STARTED", "COMPLETED", "FAILED", "IGNORED"]),
            "online_recording_url": self.bc.fake.url(),
            "allow_billing": bool(random.getrandbits(1)),
            "accounted_duration": "0" + str(accounted_duration),
            "agenda": self.bc.fake.text(),
            "summary": self.bc.fake.text(),
            "starts_at": self.bc.datetime.to_iso_string(starts_at),
            "ends_at": self.bc.datetime.to_iso_string(ends_at),
        }

        url = reverse_lazy("mentorship:academy_session")
        response = self.client.post(url, data)

        json = response.json()
        expected = {"detail": "mentee-not-found", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(self.bc.database.list_of("mentorship.MentorshipSession"), [])

    """
    🔽🔽🔽 POST creating a element, mentor and mentee can be same person
    """

    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock())
    def test__post__creating_a_element__mentor_and_mentee_can_be_same_person(self):
        utc_now = timezone.now()
        model = self.bc.database.create(
            user=1,
            role=1,
            capability="crud_mentorship_session",
            mentor_profile=1,
            consumable=1,
            mentorship_bill=1,
            mentorship_service=1,
            mentorship_service_set=1,
            profile_academy=1,
        )

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        accounted_duration = timedelta(minutes=random.randint(1, 180))
        starts_at = append_delta_to_datetime(utc_now)
        ends_at = append_delta_to_datetime(utc_now)
        data = {
            "mentor": 1,
            "service": 1,
            "mentee": 1,
            "bill": 1,
            "name": self.bc.fake.name(),
            "is_online": bool(random.getrandbits(1)),
            "latitude": get_base_number() * random.random() * 1000,
            "longitude": get_base_number() * random.random() * 1000,
            "online_meeting_url": self.bc.fake.url(),
            "online_recording_url": self.bc.fake.url(),
            "status": random.choice(["PENDING", "STARTED", "COMPLETED", "FAILED", "IGNORED"]),
            "online_recording_url": self.bc.fake.url(),
            "allow_billing": bool(random.getrandbits(1)),
            "accounted_duration": "0" + str(accounted_duration),
            "agenda": self.bc.fake.text(),
            "summary": self.bc.fake.text(),
            "starts_at": self.bc.datetime.to_iso_string(starts_at),
            "ends_at": self.bc.datetime.to_iso_string(ends_at),
        }

        url = reverse_lazy("mentorship:academy_session")
        response = self.client.post(url, data)

        json = response.json()
        expected = {"detail": "mentor-mentee-same-person", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(self.bc.database.list_of("mentorship.MentorshipSession"), [])

    """
    🔽🔽🔽 POST creating a element, passing all the fields
    """

    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock())
    def test__post__creating_a_element__passing_all_the_fields(self):
        utc_now = timezone.now()
        consumable = {"user_id": 2}
        model = self.bc.database.create(
            user=2,
            role=1,
            capability="crud_mentorship_session",
            mentor_profile=1,
            consumable=consumable,
            mentorship_bill=1,
            mentorship_service=1,
            mentorship_service_set=1,
            profile_academy=1,
        )

        self.bc.request.set_headers(academy=1)
        self.bc.request.authenticate(model.user[0])

        minutes = random.randint(1, 180)
        accounted_duration = timedelta(minutes=minutes)
        starts_at = append_delta_to_datetime(utc_now)
        ends_at = append_delta_to_datetime(utc_now)
        data = {
            "mentor": 1,
            "service": 1,
            "mentee": 2,
            "bill": 1,
            "name": self.bc.fake.name(),
            "is_online": bool(random.getrandbits(1)),
            "latitude": get_base_number() * random.random() * 1000,
            "longitude": get_base_number() * random.random() * 1000,
            "online_meeting_url": self.bc.fake.url(),
            "online_recording_url": self.bc.fake.url(),
            "status": random.choice(["PENDING", "STARTED", "COMPLETED", "FAILED", "IGNORED"]),
            "online_recording_url": self.bc.fake.url(),
            "allow_billing": bool(random.getrandbits(1)),
            "accounted_duration": "0" + str(accounted_duration),
            "agenda": self.bc.fake.text(),
            "summary": self.bc.fake.text(),
            "starts_at": self.bc.datetime.to_iso_string(starts_at),
            "ends_at": self.bc.datetime.to_iso_string(ends_at),
        }

        url = reverse_lazy("mentorship:academy_session")
        response = self.client.post(url, data)

        json = response.json()
        expected = post_serializer(
            {
                **data,
                "accounted_duration": f"{minutes * 60}.0",
                "bill": {"id": 1, "status": "DUE"},
                "service": {
                    "id": model.mentorship_service.id,
                    "name": model.mentorship_service.name,
                    "slug": model.mentorship_service.slug,
                },
                "mentor": {
                    "id": model.mentor_profile.id,
                    "slug": model.mentor_profile.slug,
                    "status": model.mentor_profile.status,
                    "user": {
                        "first_name": model.mentor_profile.user.first_name,
                        "last_name": model.mentor_profile.user.last_name,
                        "email": model.mentor_profile.user.email,
                        "id": model.mentor_profile.user.id,
                    },
                },
                "mentee": {
                    "email": model.user[1].email,
                    "first_name": model.user[1].first_name,
                    "id": model.user[1].id,
                    "last_name": model.user[1].last_name,
                },
            }
        )

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        fields = ["bill", "mentee", "mentor", "service"]
        for field in fields:
            data[f"{field}_id"] = data[field]
            del data[field]

        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipSession"),
            [
                mentorship_session_columns(
                    {
                        **data,
                        "accounted_duration": accounted_duration,
                        "starts_at": starts_at,
                        "ends_at": ends_at,
                    }
                ),
            ],
        )

    """
    🔽🔽🔽 PUT capability
    """

    def test__put__without_capabilities(self):
        model = self.bc.database.create(user=1)

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_session")
        response = self.client.put(url)

        json = response.json()
        expected = {
            "detail": "You (user: 1) don't have this capability: crud_mentorship_session for academy 1",
            "status_code": 403,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    """
    🔽🔽🔽 PUT without id
    """

    def test__put__without_id(self):
        model = self.bc.database.create(user=1, role=1, capability="crud_mentorship_session", profile_academy=1)

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_session")
        data = [{}]
        response = self.client.put(url, data, format="json")

        json = response.json()
        expected = {"detail": "without-id", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of("mentorship.MentorshipSession"), [])
        self.assertEqual(self.bc.database.list_of("mentorship.MentorshipBill"), [])

    """
    🔽🔽🔽 PUT not found the MentorshipSession
    """

    def test__put__not_found(self):
        cases = [
            (1, {}, False),
            (2, {"mentorship_session": 1}, True),
        ]
        for id, kwargs, has_instance_db in cases:
            model = self.bc.database.create(
                user=1, role=1, capability="crud_mentorship_session", profile_academy=1, **kwargs
            )

            self.bc.request.set_headers(academy=id)
            self.client.force_authenticate(model.user)

            url = reverse_lazy("mentorship:academy_session")
            data = [{"id": id}]
            response = self.client.put(url, data, format="json")

            json = response.json()
            expected = {"detail": "not-found", "status_code": 404}

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
            self.assertEqual(
                self.bc.database.list_of("mentorship.MentorshipSession"),
                (
                    [
                        self.bc.format.to_dict(model.mentorship_session),
                    ]
                    if has_instance_db
                    else []
                ),
            )
            self.assertEqual(self.bc.database.list_of("mentorship.MentorshipBill"), [])

            # teardown
            self.bc.database.delete("mentorship.MentorshipSession")

    """
    🔽🔽🔽 PUT found a MentorshipSession, with one MentorProfile and MentorshipService
    """

    def test__put__found__without_required_fields(self):
        model = self.bc.database.create(
            user=1,
            role=1,
            capability="crud_mentorship_session",
            mentorship_session=1,
            mentorship_service=1,
            mentor_profile=1,
            profile_academy=1,
        )

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_session")
        data = [{"id": 1}]
        response = self.client.put(url, data, format="json")

        json = response.json()
        expected = [{"mentor": ["This field is required."]}]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipSession"),
            [
                self.bc.format.to_dict(model.mentorship_session),
            ],
        )
        self.assertEqual(self.bc.database.list_of("mentorship.MentorshipBill"), [])

    def test__put__found__with_required_fields(self):
        model = self.bc.database.create(
            user=1,
            role=1,
            capability="crud_mentorship_session",
            mentorship_session=1,
            mentorship_service=1,
            mentor_profile=1,
            profile_academy=1,
        )

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_session")
        data = [{"id": 1, "mentor": 1}]
        response = self.client.put(url, data, format="json")

        json = response.json()
        expected = [
            put_serializer(
                {
                    "id": 1,
                    "mentee": 1,
                    "service": 1,
                    "calendly_uuid": None,
                    **data[0],
                }
            )
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipSession"),
            [
                self.bc.format.to_dict(model.mentorship_session),
            ],
        )
        self.assertEqual(self.bc.database.list_of("mentorship.MentorshipBill"), [])

    """
    🔽🔽🔽 PUT with all required fields, is_online is False
    """

    def test__put__found__with_all_required_fields__is_online_as_false(self):
        mentorship_bill = {"status": random.choice(["RECALCULATE", "DUE"])}
        statuses = ["PENDING", "STARTED", "COMPLETED", "FAILED", "IGNORED"]
        current_status = random.choice(statuses)
        statuses.remove(current_status)
        mentorship_session = {"status": current_status}

        model = self.bc.database.create(
            user=1,
            role=1,
            capability="crud_mentorship_session",
            mentorship_session=mentorship_session,
            mentorship_service=1,
            mentorship_bill=mentorship_bill,
            mentor_profile=1,
            profile_academy=1,
        )

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_session_id", kwargs={"session_id": 1})
        date = timezone.now()
        data = [
            {
                "name": self.bc.fake.name(),
                "is_online": False,
                "latitude": random.random() * 180 * random.choice([1, -1]),
                "longitude": random.random() * 90 * random.choice([1, -1]),
                "longitude": random.random() * 90 * random.choice([1, -1]),
                "service": 1,
                "mentee": 1,
                "id": 1,
                "online_meeting_url": self.bc.fake.url(),
                "online_recording_url": self.bc.fake.url(),
                "status": random.choice(statuses),
                "allow_billing": bool(random.randint(0, 1)),
                "bill": 1,
                "agenda": self.bc.fake.text(),
                "summary": self.bc.fake.text(),
                "starts_at": self.bc.datetime.to_iso_string(date),
                "ends_at": self.bc.datetime.to_iso_string(date),
                "started_at": self.bc.datetime.to_iso_string(date),
                "ended_at": self.bc.datetime.to_iso_string(date),
                "mentor_joined_at": self.bc.datetime.to_iso_string(date),
                "mentor_left_at": self.bc.datetime.to_iso_string(date),
                "mentee_left_at": self.bc.datetime.to_iso_string(date),
                "mentor": 1,
            }
        ]
        response = self.client.put(url, data, format="json")

        json = response.json()
        expected = [
            put_serializer(
                {
                    "id": 1,
                    "mentee": 1,
                    "service": 1,
                    "calendly_uuid": None,
                    **data[0],
                }
            )
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        update_fields = ["bill", "mentee", "mentor", "service"]
        for key in update_fields:
            data[0][f"{key}_id"] = data[0].pop(key)

        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipSession"),
            [
                {
                    **self.bc.format.to_dict(model.mentorship_session),
                    **data[0],
                    "starts_at": date,
                    "ends_at": date,
                    "started_at": date,
                    "ended_at": date,
                    "mentor_joined_at": date,
                    "mentor_left_at": date,
                    "mentee_left_at": date,
                    "suggested_accounted_duration": timedelta(0),
                    "accounted_duration": timedelta(0),
                    "status_message": "",
                },
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipBill"),
            [
                self.bc.format.to_dict(model.mentorship_bill),
            ],
        )

    """
    🔽🔽🔽 PUT with all required fields, is_online is False, MentorshipBill finished
    """

    def test__put__found__with_all_required_fields__is_online_as_false__bill_finished(self):
        mentorship_bill = {"status": random.choice(["APPROVED", "PAID", "IGNORED"])}
        statuses = ["PENDING", "STARTED", "COMPLETED", "FAILED", "IGNORED"]
        current_status = random.choice(statuses)
        statuses.remove(current_status)
        mentorship_session = {"status": current_status}

        model = self.bc.database.create(
            user=1,
            role=1,
            capability="crud_mentorship_session",
            mentorship_session=mentorship_session,
            mentorship_service=1,
            mentorship_bill=mentorship_bill,
            mentor_profile=1,
            profile_academy=1,
        )

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_session_id", kwargs={"session_id": 1})
        date = timezone.now()
        data = [
            {
                "name": self.bc.fake.name(),
                "is_online": False,
                "latitude": random.random() * 180 * random.choice([1, -1]),
                "longitude": random.random() * 90 * random.choice([1, -1]),
                "longitude": random.random() * 90 * random.choice([1, -1]),
                "service": 1,
                "mentee": 1,
                "online_meeting_url": self.bc.fake.url(),
                "online_recording_url": self.bc.fake.url(),
                "status": random.choice(statuses),
                "allow_billing": bool(random.randint(0, 1)),
                "bill": 1,
                "id": 1,
                "agenda": self.bc.fake.text(),
                "summary": self.bc.fake.text(),
                "starts_at": self.bc.datetime.to_iso_string(date),
                "ends_at": self.bc.datetime.to_iso_string(date),
                "started_at": self.bc.datetime.to_iso_string(date),
                "ended_at": self.bc.datetime.to_iso_string(date),
                "mentor_joined_at": self.bc.datetime.to_iso_string(date),
                "mentor_left_at": self.bc.datetime.to_iso_string(date),
                "mentee_left_at": self.bc.datetime.to_iso_string(date),
                "mentor": 1,
            }
        ]
        response = self.client.put(url, data, format="json")

        json = response.json()
        expected = {"detail": "trying-to-change-a-closed-bill", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipSession"),
            [
                {
                    **self.bc.format.to_dict(model.mentorship_session),
                },
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipBill"),
            [
                self.bc.format.to_dict(model.mentorship_bill),
            ],
        )

    """
    🔽🔽🔽 PUT passing a MentorshipBill with some MentorshipSession without MentorshipService
    """

    def test__put__found__passing_a_bill_with_some_session_without_service(self):
        mentorship_bill = {"status": "DUE"}
        statuses = ["PENDING", "STARTED", "COMPLETED", "FAILED", "IGNORED"]
        current_status = random.choice(statuses)
        statuses.remove(current_status)
        mentorship_sessions = [
            {
                "status": current_status,
                "bill_id": 1,
                "service_id": 1,
            },
            {
                "status": current_status,
                "bill_id": 1,
                "service_id": None,
            },
        ]

        model = self.bc.database.create(
            user=1,
            role=1,
            capability="crud_mentorship_session",
            mentorship_session=mentorship_sessions,
            mentorship_service=1,
            mentorship_bill=mentorship_bill,
            mentor_profile=1,
            profile_academy=1,
        )

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_session_id", kwargs={"session_id": 1})
        date = timezone.now()
        data = [
            {
                "name": self.bc.fake.name(),
                "is_online": False,
                "latitude": random.random() * 180 * random.choice([1, -1]),
                "longitude": random.random() * 90 * random.choice([1, -1]),
                "longitude": random.random() * 90 * random.choice([1, -1]),
                "service": 1,
                "mentee": 1,
                "id": 1,
                "online_meeting_url": self.bc.fake.url(),
                "online_recording_url": self.bc.fake.url(),
                "status": random.choice(statuses),
                "allow_billing": bool(random.randint(0, 1)),
                "bill": 1,
                "agenda": self.bc.fake.text(),
                "summary": self.bc.fake.text(),
                "starts_at": self.bc.datetime.to_iso_string(date),
                "ends_at": self.bc.datetime.to_iso_string(date),
                "started_at": self.bc.datetime.to_iso_string(date),
                "ended_at": self.bc.datetime.to_iso_string(date),
                "mentor_joined_at": self.bc.datetime.to_iso_string(date),
                "mentor_left_at": self.bc.datetime.to_iso_string(date),
                "mentee_left_at": self.bc.datetime.to_iso_string(date),
                "mentor": 1,
            }
        ]
        response = self.client.put(url, data, format="json")

        json = response.json()
        expected = [
            put_serializer(
                {
                    "id": 1,
                    "mentee": 1,
                    "service": 1,
                    **data[0],
                }
            )
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        update_fields = ["bill", "mentee", "mentor", "service"]
        for key in update_fields:
            data[0][f"{key}_id"] = data[0].pop(key)

        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipSession"),
            [
                {
                    **self.bc.format.to_dict(model.mentorship_session[0]),
                    **data[0],
                    "starts_at": date,
                    "ends_at": date,
                    "started_at": date,
                    "ended_at": date,
                    "mentor_joined_at": date,
                    "mentor_left_at": date,
                    "mentee_left_at": date,
                },
                self.bc.format.to_dict(model.mentorship_session[1]),
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipBill"),
            [
                {
                    **self.bc.format.to_dict(model.mentorship_bill),
                    "status": "RECALCULATE",
                },
            ],
        )
