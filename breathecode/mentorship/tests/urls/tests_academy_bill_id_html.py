"""
Test cases for /academy/:id/member/:id
"""

import os
import urllib.parse

from django.template import loader
from django.urls.base import reverse_lazy
from django.utils import timezone
from rest_framework import status

from ..mixins import MentorshipTestCase

UTC_NOW = timezone.now()


def format_datetime(self, date):
    if date is None:
        return None

    return self.bc.datetime.to_iso_string(date)


def get_tooltip(obj):

    message = f"This mentorship should last no longer than {int(obj.mentor.service.duration.seconds/60)} min. <br />"
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
        return None


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
            "mente_joined": get_mente_joined(session),
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
                "online_meeting_url": session.mentor.online_meeting_url,
                "price_per_hour": session.mentor.price_per_hour,
                "service": {
                    "academy": {
                        "icon_url": session.mentor.service.academy.icon_url,
                        "id": session.mentor.service.academy.id,
                        "logo_url": session.mentor.service.academy.logo_url,
                        "name": session.mentor.service.academy.name,
                        "slug": session.mentor.service.academy.slug,
                    },
                    "allow_mentee_to_extend": session.mentor.service.allow_mentee_to_extend,
                    "allow_mentors_to_extend": session.mentor.service.allow_mentors_to_extend,
                    "created_at": format_datetime(self, session.mentor.service.created_at),
                    "duration": self.bc.datetime.from_timedelta(session.mentor.service.duration),
                    "id": session.mentor.service.id,
                    "language": session.mentor.service.language,
                    "logo_url": session.mentor.service.logo_url,
                    "max_duration": self.bc.datetime.from_timedelta(session.mentor.service.max_duration),
                    "missed_meeting_duration": self.bc.datetime.from_timedelta(
                        session.mentor.service.missed_meeting_duration
                    ),
                    "name": session.mentor.service.name,
                    "slug": session.mentor.service.slug,
                    "status": session.mentor.service.status,
                    "updated_at": self.bc.datetime.to_iso_string(session.mentor.service.updated_at),
                },
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
        "created_at": mentorship_bill.created_at,
        "ended_at": format_datetime(self, mentorship_bill.ended_at),
        "id": mentorship_bill.id,
        "mentor": {
            "booking_url": mentor_profile.booking_url,
            "created_at": format_datetime(self, mentor_profile.created_at),
            "id": mentor_profile.id,
            "email": mentor_profile.email,
            "online_meeting_url": mentor_profile.online_meeting_url,
            "price_per_hour": mentor_profile.price_per_hour,
            "service": {
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
                "missed_meeting_duration": self.bc.datetime.from_timedelta(mentorship_service.missed_meeting_duration),
                "name": mentorship_service.name,
                "slug": mentorship_service.slug,
                "status": mentorship_service.status,
                "updated_at": format_datetime(self, mentorship_service.updated_at),
            },
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
        "paid_at": mentorship_bill.ended_at,
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


# IMPORTANT: the loader.render_to_string in a function is inside of function render
def render_successfully(self, mentorship_bill, mentor_profile, mentorship_service, user, academy, data={}):
    request = None
    APP_URL = os.getenv("APP_URL", "")

    template = loader.get_template("mentorship_invoice.html")
    status_map = {"DUE": "UNDER_REVIEW", "APPROVED": "READY_TO_PAY", "PAID": "ALREADY PAID"}

    data = {
        "API_URL": None,
        "COMPANY_NAME": "",
        "COMPANY_CONTACT_URL": "",
        "COMPANY_LEGAL_NAME": "",
        "COMPANY_ADDRESS": "",
        "style__success": "#99ccff",
        "style__danger": "#ffcccc",
        "style__secondary": "#ededed",
        **get_serializer(self, mentorship_bill, mentor_profile, mentorship_service, user, academy, data={}),
        "status": status_map[mentorship_bill.status],
    }

    if academy:
        data["COMPANY_INFO_EMAIL"] = academy.feedback_email
        data["COMPANY_LEGAL_NAME"] = academy.legal_name or academy.name
        data["COMPANY_LOGO"] = academy.logo_url
        data["COMPANY_NAME"] = academy.name

        if "heading" not in data:
            data["heading"] = academy.name

    return template.render(data)


def render(message):
    request = None
    return loader.render_to_string(
        "message.html",
        {"MESSAGE": message, "BUTTON": None, "BUTTON_TARGET": "_blank", "LINK": None},
        request,
        using=None,
    )


def render_page_with_pending_invites(model):
    request = None
    APP_URL = os.getenv("APP_URL", "")
    profile_academies = []
    if "profile_academy" in model:
        profile_academies = (
            model.profile_academy if isinstance(model.profile_academy, list) else [model.profile_academy]
        )

    # excluding the accepted invited
    profile_academies = [x for x in profile_academies if x.status != "ACTIVE"]

    querystr = urllib.parse.urlencode({"callback": APP_URL, "token": model.token.key})
    url = os.getenv("API_URL") + "/v1/auth/academy/html/invite?" + querystr
    return loader.render_to_string(
        "academy_invite.html",
        {
            "subject": f"Invitation to study at 4Geeks.com",
            "invites": [
                {
                    "id": profile_academy.id,
                    "academy": {
                        "id": profile_academy.academy.id,
                        "name": profile_academy.academy.name,
                        "slug": profile_academy.academy.slug,
                        "timezone": profile_academy.academy.timezone,
                    },
                    "role": profile_academy.role.slug,
                    "created_at": profile_academy.created_at,
                }
                for profile_academy in profile_academies
            ],
            "LINK": url,
            "user": {
                "id": model.user.id,
                "email": model.user.email,
                "first_name": model.user.first_name,
            },
        },
        request,
    )


class AuthenticateTestSuite(MentorshipTestCase):
    """Authentication test suite"""

    """
    🔽🔽🔽 Auth
    """

    def test_without_auth(self):
        url = reverse_lazy("mentorship:academy_bill_id_html", kwargs={"id": 1})
        response = self.client.get(url)

        hash = self.bc.format.to_base64("/v1/mentorship/academy/bill/1/html")
        content = self.bc.format.from_bytes(response.content)
        expected = ""

        self.assertEqual(content, expected)
        self.assertEqual(response.url, f"/v1/auth/view/login?attempt=1&url={hash}")
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(self.bc.database.list_of("authenticate.ProfileAcademy"), [])

    """
    🔽🔽🔽 GET without MentorshipBill
    """

    def test_without_mentorship_bill(self):
        model = self.bc.database.create(user=1, token=1)

        querystring = self.bc.format.to_querystring({"token": model.token.key})
        url = reverse_lazy("mentorship:academy_bill_id_html", kwargs={"id": 1}) + f"?{querystring}"
        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render("Bill not found")

        # dump error in external files
        if content != expected:
            with open("content.html", "w") as f:
                f.write(content)

            with open("expected.html", "w") as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("authenticate.ProfileAcademy"), [])

    """
    🔽🔽🔽 GET with one MentorshipBill
    """

    def test_with_mentorship_bill(self):
        model = self.bc.database.create(user=1, token=1, mentorship_bill=1, mentorship_service=1)

        querystring = self.bc.format.to_querystring({"token": model.token.key})
        url = reverse_lazy("mentorship:academy_bill_id_html", kwargs={"id": 1}) + f"?{querystring}"
        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render_successfully(
            self,
            model.mentorship_bill,
            model.mentor_profile,
            model.mentorship_service,
            model.user,
            model.academy,
            data={},
        )

        # dump error in external files
        if content != expected:
            with open("content.html", "w") as f:
                f.write(content)

            with open("expected.html", "w") as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("authenticate.ProfileAcademy"), [])
