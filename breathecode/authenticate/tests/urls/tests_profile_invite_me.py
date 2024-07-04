"""
Test cases for /academy/:id/member/:id
"""

from unittest.mock import MagicMock, patch

from django.urls.base import reverse_lazy
from rest_framework import status

from breathecode.services import datetime_to_iso_format

from ..mixins.new_auth_test_case import AuthTestCase


def get_serializer(self, mentor_profile, academy, mentorship_service, user):
    return {
        "invites": [],
        "mentor_profiles": [
            {
                "booking_url": mentor_profile.booking_url,
                "online_meeting_url": None,
                "created_at": self.bc.datetime.to_iso_string(mentor_profile.created_at),
                "email": mentor_profile.email,
                "id": mentor_profile.id,
                "one_line_bio": mentor_profile.one_line_bio,
                "price_per_hour": mentor_profile.price_per_hour,
                "rating": mentor_profile.rating,
                "services": [
                    {
                        "academy": {
                            "icon_url": "/static/icons/picture.png",
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
                "timezone": mentor_profile.timezone,
                "updated_at": self.bc.datetime.to_iso_string(mentor_profile.updated_at),
                "user": {
                    "email": user.email,
                    "first_name": user.first_name,
                    "id": user.id,
                    "last_name": user.last_name,
                },
            }
            for mentor_profile in (mentor_profile if isinstance(mentor_profile, list) else [mentor_profile])
        ],
        "profile_academies": [],
    }


class AuthenticateTestSuite(AuthTestCase):
    """
    🔽🔽🔽 Auth
    """

    @patch("os.getenv", MagicMock(return_value="https://dot.dot"))
    def test_profile_invite_me__without_auth(self):
        url = reverse_lazy("authenticate:profile_invite_me")
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json,
            {
                "detail": "Authentication credentials were not provided.",
                "status_code": status.HTTP_401_UNAUTHORIZED,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    """
    🔽🔽🔽 Without data
    """

    @patch("os.getenv", MagicMock(return_value="https://dot.dot"))
    def test_profile_invite_me__without_data(self):
        model = self.bc.database.create(user=1)

        self.client.force_authenticate(model.user)
        url = reverse_lazy("authenticate:profile_invite_me")
        response = self.client.get(url)

        json = response.json()
        expected = {"invites": [], "mentor_profiles": [], "profile_academies": []}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    """
    🔽🔽🔽 With one UserInvite
    """

    @patch("os.getenv", MagicMock(return_value="https://dot.dot"))
    def test_profile_invite_me__with_one_user_invite(self):
        user_invite = {"email": "user@dotdotdotdot.dot"}
        user = {"email": "user@dotdotdotdot.dot"}
        model = self.bc.database.create(user=user, user_invite=user_invite)

        self.client.force_authenticate(model.user)
        url = reverse_lazy("authenticate:profile_invite_me")
        response = self.client.get(url)

        json = response.json()
        expected = {
            "invites": [
                {
                    "academy": model.user_invite.academy,
                    "cohort": model.user_invite.cohort,
                    "created_at": self.bc.datetime.to_iso_string(model.user_invite.created_at),
                    "email": model.user_invite.email,
                    "first_name": model.user_invite.first_name,
                    "id": model.user_invite.id,
                    "invite_url": f"https://dot.dot/v1/auth/member/invite/{model.user_invite.token}",
                    "last_name": model.user_invite.last_name,
                    "role": model.user_invite.role,
                    "sent_at": model.user_invite.sent_at,
                    "status": model.user_invite.status,
                    "token": model.user_invite.token,
                }
            ],
            "mentor_profiles": [],
            "profile_academies": [],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(
            self.bc.database.list_of("authenticate.UserInvite"),
            [
                self.bc.format.to_dict(model.user_invite),
            ],
        )

    """
    🔽🔽🔽 With two UserInvite
    """

    @patch("os.getenv", MagicMock(return_value="https://dot.dot"))
    def test_profile_invite_me__with_two_user_invites(self):
        user_invite = {"email": "user@dotdotdotdot.dot"}
        user = {"email": "user@dotdotdotdot.dot"}
        model = self.bc.database.create(user=user, user_invite=(2, user_invite))

        self.client.force_authenticate(model.user)
        url = reverse_lazy("authenticate:profile_invite_me")
        response = self.client.get(url)

        json = response.json()
        expected = {
            "invites": [
                {
                    "academy": user_invite.academy,
                    "cohort": user_invite.cohort,
                    "created_at": self.bc.datetime.to_iso_string(user_invite.created_at),
                    "email": user_invite.email,
                    "first_name": user_invite.first_name,
                    "id": user_invite.id,
                    "invite_url": f"https://dot.dot/v1/auth/member/invite/{user_invite.token}",
                    "last_name": user_invite.last_name,
                    "role": user_invite.role,
                    "sent_at": user_invite.sent_at,
                    "status": user_invite.status,
                    "token": user_invite.token,
                }
                for user_invite in model.user_invite
            ],
            "mentor_profiles": [],
            "profile_academies": [],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(
            self.bc.database.list_of("authenticate.UserInvite"),
            self.bc.format.to_dict(model.user_invite),
        )

    """
    🔽🔽🔽 With one MentorProfile
    """

    @patch("os.getenv", MagicMock(return_value="https://dot.dot"))
    def test_profile_invite_me__with_one_mentor_profile(self):
        model = self.bc.database.create(user=1, mentor_profile=1, mentorship_service=1)

        self.client.force_authenticate(model.user)
        url = reverse_lazy("authenticate:profile_invite_me")
        response = self.client.get(url)

        json = response.json()
        expected = get_serializer(self, model.mentor_profile, model.academy, model.mentorship_service, model.user)

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorProfile"),
            [
                self.bc.format.to_dict(model.mentor_profile),
            ],
        )

    """
    🔽🔽🔽 With two MentorProfile
    """

    @patch("os.getenv", MagicMock(return_value="https://dot.dot"))
    def test_profile_invite_me__with_two_mentor_profiles(self):
        model = self.bc.database.create(user=1, mentor_profile=2, mentorship_service=1)

        self.client.force_authenticate(model.user)
        url = reverse_lazy("authenticate:profile_invite_me")
        response = self.client.get(url)

        json = response.json()
        expected = get_serializer(self, model.mentor_profile, model.academy, model.mentorship_service, model.user)

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorProfile"),
            self.bc.format.to_dict(model.mentor_profile),
        )

    """
    🔽🔽🔽 With one ProfileAcademy
    """

    @patch("os.getenv", MagicMock(return_value="https://dot.dot"))
    def test_profile_invite_me__with_one_profile_academy(self):
        model = self.bc.database.create(user=1, profile_academy=1, role="potato")

        self.client.force_authenticate(model.user)
        url = reverse_lazy("authenticate:profile_invite_me")
        response = self.client.get(url)

        json = response.json()
        expected = {
            "invites": [],
            "mentor_profiles": [],
            "profile_academies": [
                {
                    "academy": {
                        "id": model.academy.id,
                        "name": model.academy.name,
                        "slug": model.academy.slug,
                    },
                    "address": model.profile_academy.address,
                    "created_at": self.bc.datetime.to_iso_string(model.profile_academy.created_at),
                    "email": model.profile_academy.email,
                    "first_name": model.profile_academy.first_name,
                    "id": model.profile_academy.id,
                    "invite_url": "https://dot.dot/v1/auth/academy/html/invite",
                    "last_name": model.profile_academy.last_name,
                    "phone": model.profile_academy.phone,
                    "role": {
                        "id": "potato",
                        "name": "potato",
                        "slug": "potato",
                    },
                    "status": model.profile_academy.status,
                    "user": {
                        "email": model.user.email,
                        "first_name": model.user.first_name,
                        "github": None,
                        "id": model.user.id,
                        "last_name": model.user.last_name,
                        "profile": None,
                    },
                }
            ],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(
            self.bc.database.list_of("authenticate.ProfileAcademy"),
            [
                self.bc.format.to_dict(model.profile_academy),
            ],
        )

    """
    🔽🔽🔽 With two ProfileAcademy
    """

    @patch("os.getenv", MagicMock(return_value="https://dot.dot"))
    def test_profile_invite_me__with_two_profile_academies(self):
        model = self.bc.database.create(user=1, profile_academy=2, role="potato")

        self.client.force_authenticate(model.user)
        url = reverse_lazy("authenticate:profile_invite_me")
        response = self.client.get(url)

        json = response.json()
        expected = {
            "invites": [],
            "mentor_profiles": [],
            "profile_academies": [
                {
                    "academy": {
                        "id": model.academy.id,
                        "name": model.academy.name,
                        "slug": model.academy.slug,
                    },
                    "address": profile_academy.address,
                    "created_at": self.bc.datetime.to_iso_string(profile_academy.created_at),
                    "email": profile_academy.email,
                    "first_name": profile_academy.first_name,
                    "id": profile_academy.id,
                    "invite_url": "https://dot.dot/v1/auth/academy/html/invite",
                    "last_name": profile_academy.last_name,
                    "phone": profile_academy.phone,
                    "role": {
                        "id": "potato",
                        "name": "potato",
                        "slug": "potato",
                    },
                    "status": profile_academy.status,
                    "user": {
                        "email": model.user.email,
                        "first_name": model.user.first_name,
                        "github": None,
                        "id": model.user.id,
                        "last_name": model.user.last_name,
                        "profile": None,
                    },
                }
                for profile_academy in model.profile_academy
            ],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(
            self.bc.database.list_of("authenticate.ProfileAcademy"),
            self.bc.format.to_dict(model.profile_academy),
        )
