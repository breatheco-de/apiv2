"""
This file just can contains duck tests refert to AcademyInviteView
"""

import hashlib
import random
from datetime import timedelta
from unittest.mock import MagicMock, call, patch

from django.urls.base import reverse_lazy
from django.utils import timezone
from rest_framework import status

from breathecode.utils.api_view_extensions.api_view_extension_handlers import APIViewExtensionHandlers
from breathecode.utils.datetime_integer import duration_to_str

from ..mixins import MentorshipTestCase

UTC_NOW = timezone.now()


def format_datetime(self, date):
    if date is None:
        return None

    return self.bc.datetime.to_iso_string(date)


def get_tooltip(obj):

    message = f"This mentorship should last no longer than {int(obj.service.duration.seconds/60)} min. <br />"
    if obj.started_at is None:
        message += "The mentee never joined the session. <br />"
    else:
        message += f'Started on {obj.started_at.strftime("%m/%d/%Y at %H:%M:%S")}. <br />'
        if obj.mentor_joined_at is None:
            message += f"The mentor never joined"
        elif obj.mentor_joined_at > obj.started_at:
            message += f"The mentor joined {duration_to_str(obj.mentor_joined_at - obj.started_at)} before. <br />"
        elif obj.started_at > obj.mentor_joined_at:
            message += f"The mentor joined {duration_to_str(obj.started_at - obj.mentor_joined_at)} after. <br />"

        if obj.ended_at is not None:
            message += f"The mentorship lasted {duration_to_str(obj.ended_at - obj.started_at)}. <br />"
            if (obj.ended_at - obj.started_at) > obj.mentor.service.duration:
                extra_time = (obj.ended_at - obj.started_at) - obj.mentor.service.duration
                message += f"With extra time of {duration_to_str(extra_time)}. <br />"
            else:
                message += f"No extra time detected <br />"
        else:
            message += f"The mentorship has not ended yet. <br />"
            if obj.ends_at is not None:
                message += f"But it was supposed to end after {duration_to_str(obj.ends_at - obj.started_at)} <br />"

    return message


def get_duration_string(obj):

    if obj.started_at is None:
        return "Never started"

    end_date = obj.ended_at
    if end_date is None:
        return "Never ended"

    if obj.started_at > end_date:
        return "Ended before it started"

    if (end_date - obj.started_at).days > 1:
        return f"Many days"

    return duration_to_str(obj.ended_at - obj.started_at)


def get_billed_str(obj):
    return duration_to_str(obj.accounted_duration)


def get_accounted_duration_string(self, obj):
    return duration_to_str(obj.accounted_duration)


def get_extra_time(obj):

    if obj.started_at is None or obj.ended_at is None:
        return None

    if (obj.ended_at - obj.started_at).days > 1:
        return f"Many days of extra time, probably it was never closed"

    if (obj.ended_at - obj.started_at) > obj.mentor.service.duration:
        extra_time = (obj.ended_at - obj.started_at) - obj.mentor.service.duration
        return f"Extra time of {duration_to_str(extra_time)}, the expected duration was {duration_to_str(obj.mentor.service.duration)}"
    else:
        return None


def get_mentor_late(obj):

    if obj.started_at is None or obj.mentor_joined_at is None:
        return None

    if obj.started_at > obj.mentor_joined_at and (obj.started_at - obj.mentor_joined_at).seconds > (60 * 4):
        return f"The mentor joined {duration_to_str(obj.started_at - obj.mentor_joined_at)} after. <br />"
    else:
        return None


def get_mente_joined(obj):

    if obj.started_at is None:
        return "Session did not start because mentee never joined"
    else:
        return True


def get_rating(obj):

    answer = obj.answer_set.first()
    if answer is None:
        return None
    else:
        return {}


def get_overtime_hours(obj):
    return round(obj.overtime_minutes / 60, 2)


def get_sessions(self, obj):
    sessions = obj.mentorshipsession_set.order_by("created_at").all()
    return [
        {
            "accounted_duration": session.accounted_duration,
            "billed_str": get_billed_str(session),
            "duration_string": get_duration_string(session),
            "ended_at": session.ended_at,
            "extra_time": get_extra_time(session),
            "id": session.id,
            "mentee_joined": get_mente_joined(session),
            "mentee": {
                "email": session.mentee.email,
                "first_name": session.mentee.first_name,
                "id": session.mentee.id,
                "last_name": session.mentee.last_name,
            },
            "mentee_left_at": session.mentee_left_at,
            "mentor": {
                "booking_url": session.mentor.booking_url,
                "created_at": format_datetime(self, session.mentor.created_at),
                "email": session.mentor.email,
                "id": session.mentor.id,
                "one_line_bio": session.mentor.one_line_bio,
                "online_meeting_url": session.mentor.online_meeting_url,
                "price_per_hour": session.mentor.price_per_hour,
                "rating": session.mentor.rating,
                "services": [
                    {
                        "academy": {
                            "icon_url": session.service.academy.icon_url,
                            "id": session.service.academy.id,
                            "logo_url": session.service.academy.logo_url,
                            "name": session.service.academy.name,
                            "slug": session.service.academy.slug,
                        },
                        "allow_mentee_to_extend": session.service.allow_mentee_to_extend,
                        "allow_mentors_to_extend": session.service.allow_mentors_to_extend,
                        "created_at": format_datetime(self, session.service.created_at),
                        "duration": self.bc.datetime.from_timedelta(session.service.duration),
                        "id": session.service.id,
                        "language": session.service.language,
                        "logo_url": session.service.logo_url,
                        "max_duration": self.bc.datetime.from_timedelta(session.service.max_duration),
                        "missed_meeting_duration": self.bc.datetime.from_timedelta(
                            session.service.missed_meeting_duration
                        ),
                        "name": session.service.name,
                        "slug": session.service.slug,
                        "status": session.service.status,
                        "updated_at": self.bc.datetime.to_iso_string(session.service.updated_at),
                    }
                ],
                "slug": session.mentor.slug,
                "status": session.mentor.status,
                "timezone": session.mentor.timezone,
                "updated_at": format_datetime(self, session.mentor.updated_at),
                "user": {
                    "email": session.mentor.user.email,
                    "first_name": session.mentor.user.first_name,
                    "id": session.mentor.user.id,
                    "last_name": session.mentor.user.last_name,
                },
            },
            "mentor_joined_at": session.mentor_joined_at,
            "mentor_late": get_mentor_late(session),
            "mentor_left_at": session.mentor_left_at,
            "rating": get_rating(session),
            "started_at": session.started_at,
            "status": session.status,
            "status_message": session.status_message,
            "suggested_accounted_duration": session.suggested_accounted_duration,
            "summary": session.summary,
            "tooltip": get_tooltip(session),
        }
        for session in sessions
    ]


def get_unfinished_sessions(obj):
    return []


def get_public_url():
    return "/v1/mentorship/academy/bill/1/html"


def get_serializer(self, mentorship_bill, mentor_profile, mentorship_service, user, academy, data={}):
    return {
        "academy": {
            "icon_url": academy.icon_url,
            "id": academy.id,
            "logo_url": academy.logo_url,
            "name": academy.name,
            "slug": academy.slug,
        },
        "overtime_hours": get_overtime_hours(mentorship_bill),
        "sessions": get_sessions(self, mentorship_bill),
        "unfinished_sessions": get_unfinished_sessions(mentorship_bill),
        "public_url": get_public_url(),
        "created_at": format_datetime(self, mentorship_bill.created_at),
        "ended_at": format_datetime(self, mentorship_bill.ended_at),
        "id": mentorship_bill.id,
        "mentor": {
            "booking_url": mentor_profile.booking_url,
            "created_at": format_datetime(self, mentor_profile.created_at),
            "id": mentor_profile.id,
            "one_line_bio": mentor_profile.one_line_bio,
            "email": mentor_profile.email,
            "online_meeting_url": mentor_profile.online_meeting_url,
            "price_per_hour": mentor_profile.price_per_hour,
            "rating": mentor_profile.rating,
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
                    "created_at": format_datetime(self, mentorship_service.created_at),
                    "duration": self.bc.datetime.from_timedelta(mentorship_service.duration),
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
                    "updated_at": format_datetime(self, mentorship_service.updated_at),
                }
            ],
            "slug": mentor_profile.slug,
            "timezone": mentor_profile.timezone,
            "status": mentor_profile.status,
            "updated_at": format_datetime(self, mentor_profile.updated_at),
            "user": {
                "email": user.email,
                "first_name": user.first_name,
                "id": user.id,
                "last_name": user.last_name,
            },
        },
        "overtime_minutes": float(mentorship_bill.overtime_minutes),
        "paid_at": format_datetime(self, mentorship_bill.ended_at),
        "reviewer": {
            "email": user.email,
            "first_name": user.first_name,
            "id": user.id,
            "last_name": user.last_name,
        },
        "started_at": format_datetime(self, mentorship_bill.ended_at),
        "status": mentorship_bill.status,
        "total_duration_in_hours": float(mentorship_bill.total_duration_in_hours),
        "total_duration_in_minutes": float(mentorship_bill.total_duration_in_minutes),
        "total_price": float(mentorship_bill.total_price),
        **data,
    }


def put_serializer(self, mentorship_bill, mentor_profile, mentorship_service, user, academy, data={}):
    return {
        "created_at": format_datetime(self, mentorship_bill.created_at),
        "ended_at": format_datetime(self, mentorship_bill.ended_at),
        "id": mentorship_bill.id,
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
                    "created_at": self.bc.datetime.to_iso_string(mentorship_service.created_at),
                    "duration": self.bc.datetime.from_timedelta(mentorship_service.duration),
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
        "overtime_minutes": float(mentorship_bill.overtime_minutes),
        "paid_at": format_datetime(self, mentorship_bill.ended_at),
        "reviewer": {
            "email": user.email,
            "first_name": user.first_name,
            "id": user.id,
            "last_name": user.last_name,
        },
        "started_at": format_datetime(self, mentorship_bill.ended_at),
        "status": mentorship_bill.status,
        "total_duration_in_hours": float(mentorship_bill.total_duration_in_hours),
        "total_duration_in_minutes": float(mentorship_bill.total_duration_in_minutes),
        "total_price": float(mentorship_bill.total_price),
        **data,
    }


def mentorship_session_columns(data={}):
    return {
        "accounted_duration": None,
        "agenda": None,
        "allow_billing": False,
        "bill_id": None,
        "ended_at": None,
        "ends_at": None,
        "id": 1,
        "is_online": False,
        "latitude": None,
        "longitude": None,
        "mentee_id": None,
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
        url = reverse_lazy("mentorship:academy_bill_id", kwargs={"bill_id": 1})
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

        url = reverse_lazy("mentorship:academy_bill_id", kwargs={"bill_id": 1})
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

        url = reverse_lazy("mentorship:academy_bill_id", kwargs={"bill_id": 1})
        response = self.client.get(url)

        json = response.json()
        expected = {
            "detail": "You (user: 1) don't have this capability: read_mentorship_bill for academy 1",
            "status_code": 403,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    """
    🔽🔽🔽 GET without data
    """

    def test__get__without_data(self):
        model = self.bc.database.create(user=1, role=1, capability="read_mentorship_bill", profile_academy=1)

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_bill_id", kwargs={"bill_id": 1})
        response = self.client.get(url)

        json = response.json()
        expected = {"detail": "not-found", "status_code": 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    """
    🔽🔽🔽 GET with one MentorshipSession, MentorProfile and MentorshipService
    """

    def test__get__with_one_mentor_profile(self):
        model = self.bc.database.create(
            user=1,
            role=1,
            capability="read_mentorship_bill",
            mentorship_session=1,
            mentor_profile=1,
            mentorship_service=1,
            mentorship_bill=1,
            profile_academy=1,
        )

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_bill_id", kwargs={"bill_id": 1})
        response = self.client.get(url)

        json = response.json()
        expected = get_serializer(
            self,
            model.mentorship_bill,
            model.mentor_profile,
            model.mentorship_service,
            model.user,
            model.academy,
            data={},
        )

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipBill"), [self.bc.format.to_dict(model.mentorship_bill)]
        )

    """
    🔽🔽🔽 Spy the extensions
    """

    @patch.object(APIViewExtensionHandlers, "_spy_extensions", MagicMock())
    @patch.object(APIViewExtensionHandlers, "_spy_extension_arguments", MagicMock())
    def test__get__spy_extensions(self):
        model = self.bc.database.create(
            user=1, role=1, capability="read_mentorship_bill", mentorship_session=1, profile_academy=1
        )

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_bill_id", kwargs={"bill_id": 1})
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
    🔽🔽🔽 PUT capability
    """

    def test__put__without_capabilities(self):
        model = self.bc.database.create(user=1)

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_bill_id", kwargs={"bill_id": 1})
        response = self.client.put(url)

        json = response.json()
        expected = {
            "detail": "You (user: 1) don't have this capability: crud_mentorship_bill for academy 1",
            "status_code": 403,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    """
    🔽🔽🔽 PUT without data
    """

    def test__put__without_data(self):
        model = self.bc.database.create(user=1, role=1, capability="crud_mentorship_bill", profile_academy=1)

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_bill_id", kwargs={"bill_id": 1})
        response = self.client.put(url)

        json = response.json()
        expected = {"detail": "not-found", "status_code": 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    """
    🔽🔽🔽 PUT with one MentorshipSession, MentorProfile and MentorshipService
    """

    def test__put__with_one_mentor_profile(self):
        model = self.bc.database.create(
            user=1,
            role=1,
            capability="crud_mentorship_bill",
            mentorship_session=1,
            mentor_profile=1,
            mentorship_service=1,
            mentorship_bill=1,
            profile_academy=1,
        )

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_bill_id", kwargs={"bill_id": 1})
        response = self.client.put(url)

        json = response.json()
        expected = put_serializer(
            self,
            model.mentorship_bill,
            model.mentor_profile,
            model.mentorship_service,
            model.user,
            model.academy,
            data={},
        )

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipBill"),
            [
                self.bc.format.to_dict(model.mentorship_bill),
            ],
        )

    """
    🔽🔽🔽 PUT with one MentorshipSession, MentorProfile and MentorshipService, edit status of dirty bill
    """

    def test__put__with_one_mentor_profile__edit_status_of_dirty_bill(self):
        mentorship_bill = {"status": "RECALCULATE"}
        model = self.bc.database.create(
            user=1,
            role=1,
            capability="crud_mentorship_bill",
            mentorship_session=1,
            mentor_profile=1,
            mentorship_service=1,
            mentorship_bill=mentorship_bill,
            profile_academy=1,
        )

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_bill_id", kwargs={"bill_id": 1})
        data = {"status": "PAID"}
        response = self.client.put(url, data, format="json")

        json = response.json()
        expected = {"detail": "trying-edit-status-to-dirty-bill", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipBill"),
            [
                self.bc.format.to_dict(model.mentorship_bill),
            ],
        )

    """
    🔽🔽🔽 PUT with one MentorshipSession, MentorProfile and MentorshipService, passing forbidden fields
    """

    def test__put__with_one_mentor_profile__passing_all_forbidden_fields(self):
        model = self.bc.database.create(
            user=1,
            role=1,
            capability="crud_mentorship_bill",
            mentorship_session=1,
            mentor_profile=1,
            mentorship_service=1,
            mentorship_bill=1,
            profile_academy=1,
        )

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        created_at = timezone.now()
        updated_at = timezone.now()
        data = {
            "created_at": self.bc.datetime.to_iso_string(created_at),
            "updated_at": self.bc.datetime.to_iso_string(updated_at),
            "academy": 2,
            "reviewer": 2,
            "total_duration_in_minutes": random.random() * 100,
            "total_duration_in_hours": random.random() * 100,
            "total_price": random.random() * 100,
            "overtime_minutes": random.random() * 100,
        }

        url = reverse_lazy("mentorship:academy_bill_id", kwargs={"bill_id": 1})
        response = self.client.put(url, data)

        json = response.json()
        expected = put_serializer(
            self,
            model.mentorship_bill,
            model.mentor_profile,
            model.mentorship_service,
            model.user,
            model.academy,
            data={},
        )

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipBill"),
            [
                self.bc.format.to_dict(model.mentorship_bill),
            ],
        )

    """
    🔽🔽🔽 PUT with one MentorshipSession, MentorProfile and MentorshipService, passing all valid fields
    """

    def test__put__with_one_mentor_profile__passing_all_fields(self):
        model = self.bc.database.create(
            user=1,
            role=1,
            capability="crud_mentorship_bill",
            mentorship_session=1,
            mentor_profile=1,
            mentorship_service=1,
            mentorship_bill=1,
            profile_academy=1,
        )

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        started_at = timezone.now()
        ended_at = timezone.now()
        paid_at = timezone.now()
        data = {
            "status": random.choice(["DUE", "APPROVED", "PAID", "IGNORED"]),
            "status_mesage": self.bc.fake.text(),
            "started_at": self.bc.datetime.to_iso_string(started_at),
            "ended_at": self.bc.datetime.to_iso_string(ended_at),
            "paid_at": self.bc.datetime.to_iso_string(paid_at),
        }

        url = reverse_lazy("mentorship:academy_bill_id", kwargs={"bill_id": 1})
        response = self.client.put(url, data)

        data_fixed = data.copy()
        del data_fixed["status_mesage"]

        json = response.json()
        expected = put_serializer(
            self,
            model.mentorship_bill,
            model.mentor_profile,
            model.mentorship_service,
            model.user,
            model.academy,
            data=data_fixed,
        )

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipBill"),
            [
                {
                    **self.bc.format.to_dict(model.mentorship_bill),
                    **data,
                    "started_at": started_at,
                    "ended_at": ended_at,
                    "paid_at": paid_at,
                },
            ],
        )

    """
    🔽🔽🔽 PUT trying bulk mode
    """

    def test__put__trying_bulk_mode(self):
        model = self.bc.database.create(user=1, role=1, capability="crud_mentorship_bill", profile_academy=1)

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_bill_id", kwargs={"bill_id": 1})
        data = [{"id": 1}, {"id": 2}]
        response = self.client.put(url, data, format="json")

        json = response.json()
        expected = {"detail": "bulk-mode-and-bill-id", "status_code": 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    """
    🔽🔽🔽 DELETE capability
    """

    def test__delete__without_capabilities(self):
        model = self.bc.database.create(user=1)

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_bill_id", kwargs={"bill_id": 1})
        response = self.client.delete(url)

        json = response.json()
        expected = {
            "detail": "You (user: 1) don't have this capability: crud_mentorship_bill for academy 1",
            "status_code": 403,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    """
    🔽🔽🔽 DELETE without data
    """

    def test__delete__without_data(self):
        model = self.bc.database.create(user=1, role=1, capability="crud_mentorship_bill", profile_academy=1)

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_bill_id", kwargs={"bill_id": 1})
        response = self.client.delete(url)

        json = response.json()
        expected = {"detail": "not-found", "status_code": 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.bc.database.list_of("mentorship.MentorshipBill"), [])

    """
    🔽🔽🔽 DELETE with valid status
    """

    def test__delete__with_data(self):
        statuses = ["DUE", "APPROVED", "IGNORED"]
        for current in statuses:
            mentorship_bill = {"status": current}
            model = self.bc.database.create(
                user=1, role=1, capability="crud_mentorship_bill", profile_academy=1, mentorship_bill=mentorship_bill
            )

            self.bc.request.set_headers(academy=model.academy.id)
            self.client.force_authenticate(model.user)

            url = reverse_lazy("mentorship:academy_bill_id", kwargs={"bill_id": model.mentorship_bill.id})
            response = self.client.delete(url)

            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
            self.assertEqual(self.bc.database.list_of("mentorship.MentorshipBill"), [])

    """
    🔽🔽🔽 DELETE with status PAID
    """

    def test__delete__with_data__status_paid(self):
        mentorship_bill = {"status": "PAID"}
        model = self.bc.database.create(
            user=1, role=1, capability="crud_mentorship_bill", profile_academy=1, mentorship_bill=mentorship_bill
        )

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_bill_id", kwargs={"bill_id": 1})
        response = self.client.delete(url)

        json = response.json()
        expected = {"detail": "paid-bill", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipBill"),
            [
                self.bc.format.to_dict(model.mentorship_bill),
            ],
        )
