"""
This file just can contains duck tests refert to AcademyInviteView
"""

import hashlib
from datetime import timedelta
from unittest.mock import MagicMock, call, patch

from django.urls.base import reverse_lazy
from django.utils import timezone
from rest_framework import status

import breathecode.mentorship.actions as actions
from breathecode.mentorship.caches import MentorProfileCache
from breathecode.utils.api_view_extensions.api_view_extension_handlers import APIViewExtensionHandlers

from ..mixins import MentorshipTestCase

UTC_NOW = timezone.now()


def get_serializer(self, mentor_profile, mentorship_service, user, data={}):
    return {
        "booking_url": mentor_profile.booking_url,
        "created_at": self.bc.datetime.to_iso_string(mentor_profile.created_at),
        "email": mentor_profile.email,
        "id": mentor_profile.id,
        "one_line_bio": mentor_profile.one_line_bio,
        "online_meeting_url": mentor_profile.online_meeting_url,
        "price_per_hour": mentor_profile.price_per_hour,
        "rating": mentor_profile.rating,
        "services": [
            {
                "academy": {
                    "icon_url": mentorship_service.academy.icon_url,
                    "id": mentorship_service.academy.id,
                    "logo_url": mentorship_service.academy.logo_url,
                    "name": mentorship_service.academy.name,
                    "slug": mentorship_service.academy.slug,
                },
                "allow_mentee_to_extend": mentorship_service.allow_mentee_to_extend,
                "allow_mentors_to_extend": mentorship_service.allow_mentors_to_extend,
                "created_at": self.bc.datetime.to_iso_string(mentorship_service.created_at),
                "duration": self.bc.datetime.from_timedelta(mentorship_service.duration),
                "id": mentorship_service.id,
                "language": mentorship_service.language,
                "logo_url": mentorship_service.logo_url,
                "max_duration": self.bc.datetime.from_timedelta(mentorship_service.max_duration),
                "missed_meeting_duration": self.bc.datetime.from_timedelta(mentorship_service.missed_meeting_duration),
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
        **data,
    }


def post_serializer(self, mentorship_service, user, data={}):
    return {
        "id": 0,
        "one_line_bio": None,
        "slug": "",
        "user": {
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
        },
        "services": [
            {
                "id": mentorship_service.id,
                "slug": mentorship_service.slug,
                "name": mentorship_service.name,
                "status": mentorship_service.status,
                "academy": {
                    "id": mentorship_service.academy.id,
                    "slug": mentorship_service.academy.slug,
                    "name": mentorship_service.academy.name,
                    "logo_url": mentorship_service.academy.logo_url,
                    "icon_url": mentorship_service.academy.icon_url,
                },
                "logo_url": mentorship_service.logo_url,
                "duration": self.bc.datetime.from_timedelta(mentorship_service.duration),
                "language": mentorship_service.language,
                "allow_mentee_to_extend": mentorship_service.allow_mentee_to_extend,
                "allow_mentors_to_extend": mentorship_service.allow_mentors_to_extend,
                "max_duration": self.bc.datetime.from_timedelta(mentorship_service.max_duration),
                "missed_meeting_duration": self.bc.datetime.from_timedelta(mentorship_service.missed_meeting_duration),
                "created_at": self.bc.datetime.to_iso_string(mentorship_service.created_at),
                "updated_at": self.bc.datetime.to_iso_string(mentorship_service.updated_at),
                "description": mentorship_service.description,
            }
        ],
        "status": "INVITED",
        "price_per_hour": 20.0,
        "rating": None,
        "booking_url": None,
        "online_meeting_url": None,
        "timezone": None,
        "syllabus": [],
        "email": None,
        "created_at": self.bc.datetime.to_iso_string(UTC_NOW),
        "updated_at": self.bc.datetime.to_iso_string(UTC_NOW),
        **data,
    }


def mentor_profile_columns(data={}):
    token = hashlib.sha1((str(data["slug"] if "slug" in data else "") + str(UTC_NOW)).encode("UTF-8")).hexdigest()
    return {
        "bio": None,
        "booking_url": None,
        "email": None,
        "id": 0,
        "name": "",
        "one_line_bio": None,
        "calendly_uuid": None,
        "online_meeting_url": None,
        "price_per_hour": 0,
        "rating": None,
        "slug": "mirai-nikki",
        "status": "INVITED",
        "timezone": None,
        "token": token,
        "user_id": 0,
        "academy_id": 0,
        "availability_report": [],
        **data,
    }


class AcademyServiceTestSuite(MentorshipTestCase):
    """
    🔽🔽🔽 Auth
    """

    def test__get__without_auth(self):
        url = reverse_lazy("mentorship:academy_mentor")
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

        url = reverse_lazy("mentorship:academy_mentor")
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

        url = reverse_lazy("mentorship:academy_mentor")
        response = self.client.get(url)

        json = response.json()
        expected = {
            "detail": "You (user: 1) don't have this capability: read_mentorship_mentor for academy 1",
            "status_code": 403,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    """
    🔽🔽🔽 GET without data
    """

    def test__get__without_data(self):
        model = self.bc.database.create(user=1, role=1, capability="read_mentorship_mentor", profile_academy=1)

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_mentor")
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    """
    🔽🔽🔽 GET with one MentorProfile
    """

    def test__get__with_one_mentor_profile(self):
        model = self.bc.database.create(
            user=1,
            role=1,
            capability="read_mentorship_mentor",
            mentor_profile=1,
            mentorship_service=1,
            profile_academy=1,
        )

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_mentor")
        response = self.client.get(url)

        json = response.json()
        expected = [
            get_serializer(self, model.mentor_profile, model.mentorship_service, model.user),
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorProfile"),
            [
                self.bc.format.to_dict(model.mentor_profile),
            ],
        )

    """
    🔽🔽🔽 GET with two MentorProfile
    """

    def test__get__with_two_mentor_profile(self):
        model = self.bc.database.create(
            user=1,
            role=1,
            capability="read_mentorship_mentor",
            mentor_profile=2,
            mentorship_service=1,
            profile_academy=1,
        )

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_mentor")
        response = self.client.get(url)

        json = response.json()
        mentor_profile = sorted(model.mentor_profile, key=lambda x: x.created_at, reverse=True)
        expected = [
            get_serializer(self, mentor_profile[0], model.mentorship_service, model.user),
            get_serializer(self, mentor_profile[1], model.mentorship_service, model.user),
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorProfile"), self.bc.format.to_dict(model.mentor_profile)
        )

    """
    🔽🔽🔽 GET with two MentorProfile passing service in querystring
    """

    def test__get__with_two_mentor_profile__passing_bad_service(self):
        mentorship_service = {"slug": self.bc.fake.slug()}
        model = self.bc.database.create(
            user=1,
            role=1,
            capability="read_mentorship_mentor",
            mentor_profile=2,
            mentorship_service=mentorship_service,
            profile_academy=1,
        )

        self.bc.request.set_headers(academy=model.academy.id)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_mentor") + f"?services={self.bc.fake.slug()}"
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorProfile"),
            self.bc.format.to_dict(model.mentor_profile),
        )

        self.bc.database.delete("mentorship.MentorProfile")

    def test__get__with_two_mentor_profile__passing_service(self):
        slug = self.bc.fake.slug()
        mentorship_service = {"slug": slug}
        model = self.bc.database.create(
            user=1,
            role=1,
            capability="read_mentorship_mentor",
            mentor_profile=2,
            mentorship_service=mentorship_service,
            profile_academy=1,
        )

        self.bc.request.set_headers(academy=model.academy.id)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_mentor") + f"?service={slug}"
        response = self.client.get(url)

        json = response.json()
        mentor_profile = sorted(model.mentor_profile, key=lambda x: x.created_at, reverse=True)
        expected = [
            get_serializer(self, mentor_profile[0], model.mentorship_service, model.user),
            get_serializer(self, mentor_profile[1], model.mentorship_service, model.user),
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorProfile"),
            self.bc.format.to_dict(model.mentor_profile),
        )

        self.bc.database.delete("mentorship.MentorProfile")

    """
    🔽🔽🔽 GET passing like
    """

    def test__get__mentor__passing_like_wrong(self):
        model = self.bc.database.create(
            user=[
                {
                    "id": 1,
                    "first_name": "John",
                    "email": "john@example.com",
                },
                {
                    "id": 2,
                    "first_name": "Carl",
                    "email": "carl@example.com",
                },
            ],
            role=1,
            capability="read_mentorship_mentor",
            mentor_profile=[
                {
                    "user_id": 1,
                },
                {
                    "user_id": 2,
                },
            ],
            mentorship_service=1,
            profile_academy=1,
        )

        self.bc.request.set_headers(academy=model.academy.id)
        self.bc.request.authenticate(model.user[0])

        url = reverse_lazy("mentorship:academy_mentor") + f"?like=luke"
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.bc.database.delete("mentorship.MentorProfile")

    def test__get__mentor__passing_like(self):
        model = self.bc.database.create(
            user=[
                {
                    "id": 1,
                    "first_name": "John",
                    "email": "john@example.com",
                },
                {
                    "id": 2,
                    "first_name": "Carl",
                    "email": "carl@example.com",
                },
            ],
            role=1,
            capability="read_mentorship_mentor",
            mentor_profile=[
                {
                    "user_id": 1,
                },
                {
                    "user_id": 2,
                },
            ],
            mentorship_service=1,
            profile_academy=1,
        )

        self.bc.request.set_headers(academy=model.academy.id)
        self.bc.request.authenticate(model.user[0])

        url = reverse_lazy("mentorship:academy_mentor") + f"?like=john"
        response = self.client.get(url)

        json = response.json()
        expected = [
            get_serializer(self, model.mentor_profile[0], model.mentorship_service, model.user[0]),
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.bc.database.delete("mentorship.MentorProfile")

    """
    🔽🔽🔽 GET with two MentorProfile passing status in querystring
    """

    def test__get__with_two_mentor_profile__passing_bad_status(self):
        statuses = ["INVITED", "ACTIVE", "UNLISTED", "INNACTIVE"]

        for current_status in range(0, 3):
            bad_statuses = ",".join([x for x in statuses if x != current_status])

            mentor_profile = {"status": current_status}
            model = self.bc.database.create(
                user=1,
                role=1,
                capability="read_mentorship_mentor",
                mentor_profile=(2, mentor_profile),
                profile_academy=1,
            )

            self.bc.request.set_headers(academy=model.academy.id)
            self.client.force_authenticate(model.user)

            url = reverse_lazy("mentorship:academy_mentor") + f"?status={bad_statuses}"
            response = self.client.get(url)

            json = response.json()
            expected = []

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(
                self.bc.database.list_of("mentorship.MentorProfile"),
                self.bc.format.to_dict(model.mentor_profile),
            )

            self.bc.database.delete("mentorship.MentorProfile")

    def test__get__with_two_mentor_profile__passing_status(self):
        statuses = ["INVITED", "ACTIVE", "UNLISTED", "INNACTIVE"]

        for n in range(0, 4):
            # 0, 1, 10, 11, 0
            first_bin_key = bin(n).replace("0b", "")[-2:]
            first_key = int(first_bin_key, 2)
            first_status = statuses[first_key]

            # 0, 1, 10, 11, 0
            second_bin_key = bin(n + 1).replace("0b", "")[-2:]
            second_key = int(second_bin_key, 2)
            second_status = statuses[second_key]

            mentor_profiles = [{"status": x} for x in [first_status, second_status]]
            model = self.bc.database.create(
                user=1,
                role=1,
                capability="read_mentorship_mentor",
                mentor_profile=mentor_profiles,
                mentorship_service=1,
                profile_academy=1,
            )

            self.bc.request.set_headers(academy=model.academy.id)
            self.client.force_authenticate(model.user)

            url = reverse_lazy("mentorship:academy_mentor") + f"?status={first_status},{second_status}"
            response = self.client.get(url)

            json = response.json()
            mentor_profile = sorted(model.mentor_profile, key=lambda x: x.created_at, reverse=True)
            expected = [
                get_serializer(
                    self, mentor_profile[0], model.mentorship_service, model.user, data={"status": second_status}
                ),
                get_serializer(
                    self, mentor_profile[1], model.mentorship_service, model.user, data={"status": first_status}
                ),
            ]

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(
                self.bc.database.list_of("mentorship.MentorProfile"),
                self.bc.format.to_dict(model.mentor_profile),
            )

            self.bc.database.delete("mentorship.MentorProfile")

    """
    🔽🔽🔽 GET with two MentorProfile passing syllabus in querystring
    """

    def test__get__with_two_mentor_profile__passing_bad_syllabus(self):
        slug = self.bc.fake.slug()
        model = self.bc.database.create(
            user=1, role=1, capability="read_mentorship_mentor", mentor_profile=1, syllabus=1, profile_academy=1
        )

        self.bc.request.set_headers(academy=model.academy.id)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_mentor") + f"?syllabus={slug}"
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorProfile"),
            [
                self.bc.format.to_dict(model.mentor_profile),
            ],
        )

        self.bc.database.delete("mentorship.MentorProfile")

    def test__get__with_two_mentor_profile__passing_syllabus(self):
        slug = self.bc.fake.slug()
        syllabus = {"slug": slug}
        profile_academy = {
            "first_name": self.bc.fake.first_name(),
            "last_name": self.bc.fake.last_name(),
            "email": self.bc.fake.email(),
        }
        model = self.bc.database.create(
            user=1,
            role=1,
            capability="read_mentorship_mentor",
            mentor_profile=1,
            mentorship_service=1,
            syllabus=syllabus,
            profile_academy=profile_academy,
        )

        self.bc.request.set_headers(academy=model.academy.id)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_mentor") + f"?syllabus={slug}"
        response = self.client.get(url)

        json = response.json()
        expected = [
            get_serializer(self, model.mentor_profile, model.mentorship_service, model.user),
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorProfile"),
            [
                self.bc.format.to_dict(model.mentor_profile),
            ],
        )

        self.bc.database.delete("mentorship.MentorProfile")

    def test__get__with_two_mentor_profile_with_two_syllabus__passing__syllabus(self):
        slug_1 = self.bc.fake.slug()
        slug_2 = self.bc.fake.slug()
        syllabus = [{"slug": slug_1}, {"slug": slug_2}]
        profile_academy = {
            "first_name": self.bc.fake.first_name(),
            "last_name": self.bc.fake.last_name(),
            "email": self.bc.fake.email(),
        }
        model_syllabus = self.bc.database.create(syllabus=syllabus)
        model = self.bc.database.create(
            user=1,
            role=1,
            capability="read_mentorship_mentor",
            mentor_profile={"syllabus": [model_syllabus.syllabus[0], model_syllabus.syllabus[1]]},
            mentorship_service=1,
            syllabus=syllabus,
            profile_academy=profile_academy,
        )

        self.bc.request.set_headers(academy=model.academy.id)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_mentor") + f"?syllabus={slug_1},{slug_2}"
        response = self.client.get(url)

        json = response.json()
        expected = [
            get_serializer(self, model.mentor_profile, model.mentorship_service, model.user),
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorProfile"),
            [
                self.bc.format.to_dict(model.mentor_profile),
            ],
        )

        self.bc.database.delete("mentorship.MentorProfile")

    """
    🔽🔽🔽 Spy the extensions
    """

    @patch.object(APIViewExtensionHandlers, "_spy_extensions", MagicMock())
    @patch.object(APIViewExtensionHandlers, "_spy_extension_arguments", MagicMock())
    def test__get__spy_extensions(self):
        model = self.bc.database.create(
            user=1, role=1, capability="read_mentorship_mentor", mentor_profile=1, profile_academy=1
        )

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_mentor")
        self.client.get(url)

        self.assertEqual(
            APIViewExtensionHandlers._spy_extensions.call_args_list,
            [
                call(
                    ["CacheExtension", "LanguageExtension", "LookupExtension", "PaginationExtension", "SortExtension"]
                ),
            ],
        )

        self.bc.check.calls(
            APIViewExtensionHandlers._spy_extension_arguments.call_args_list,
            [
                call(cache=MentorProfileCache, sort="-created_at", paginate=True),
            ],
        )

    """
    🔽🔽🔽 POST capability
    """

    def test__post__without_capabilities(self):
        model = self.bc.database.create(user=1)

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_mentor")
        response = self.client.post(url)

        json = response.json()
        expected = {
            "detail": "You (user: 1) don't have this capability: crud_mentorship_mentor for academy 1",
            "status_code": 403,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    """
    🔽🔽🔽 POST without slug in the field
    """

    def test__post__without_slug_fields_in_body(self):
        model = self.bc.database.create(user=1, role=1, capability="crud_mentorship_mentor", profile_academy=1)

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_mentor")
        response = self.client.post(url)

        json = response.json()
        expected = {"detail": "missing-slug-field", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    """
    🔽🔽🔽 POST without required fields in body
    """

    def test__post__without_required_fields_in_body(self):
        model = self.bc.database.create(user=1, role=1, capability="crud_mentorship_mentor", profile_academy=1)

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_mentor")
        data = {"slug": "mirai-nikki", "name": "Mirai Nikki"}
        response = self.client.post(url, data, format="json")

        json = response.json()
        expected = {
            "price_per_hour": ["This field is required."],
            "services": ["This field is required."],
            "user": ["This field is required."],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of("mentorship.MentorProfile"), [])

    """
    🔽🔽🔽 POST creating a element
    """

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__post__creating_a_elements(self):
        email = self.bc.fake.email()
        profile_academy = {"name": self.bc.fake.name(), "email": email}
        model = self.bc.database.create(
            user=1, role=1, capability="crud_mentorship_mentor", profile_academy=profile_academy, mentorship_service=1
        )

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_mentor")
        data = {"slug": "mirai-nikki", "name": "Mirai Nikki", "price_per_hour": 20, "services": [1], "user": 1}
        response = self.client.post(url, data, format="json")

        json = response.json()
        expected = post_serializer(
            self,
            model.mentorship_service,
            model.user,
            data={
                "id": 1,
                "slug": "mirai-nikki",
                "email": email,
            },
        )

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorProfile"),
            [
                mentor_profile_columns(
                    {
                        "id": 1,
                        "name": "Mirai Nikki",
                        "slug": "mirai-nikki",
                        "bio": None,
                        "user_id": 1,
                        "academy_id": 1,
                        "price_per_hour": 20.0,
                        "email": email,
                    }
                ),
            ],
        )

        mentor_profile = self.bc.database.get("mentorship.MentorProfile", 1, dict=False)
        self.bc.check.queryset_with_pks(mentor_profile.services.all(), [1])

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__post__creating_a_element_taking_email_from_user(self):
        profile_academy = {
            "first_name": self.bc.fake.name(),
            "last_name": self.bc.fake.name(),
        }
        model = self.bc.database.create(
            user=1, role=1, capability="crud_mentorship_mentor", profile_academy=profile_academy, mentorship_service=1
        )

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_mentor")
        data = {"slug": "mirai-nikki", "name": "Mirai Nikki", "price_per_hour": 20, "services": [1], "user": 1}
        response = self.client.post(url, data, format="json")

        json = response.json()
        expected = post_serializer(
            self, model.mentorship_service, model.user, data={"id": 1, "slug": "mirai-nikki", "email": model.user.email}
        )

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorProfile"),
            [
                mentor_profile_columns(
                    {
                        "id": 1,
                        "name": "Mirai Nikki",
                        "slug": "mirai-nikki",
                        "bio": None,
                        "user_id": 1,
                        "academy_id": 1,
                        "price_per_hour": 20.0,
                        "email": model.user.email,
                    }
                ),
            ],
        )

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("breathecode.mentorship.actions.mentor_is_ready", MagicMock(side_effect=Exception("hello")))
    def test__post__with_one_mentor_profile__changing_to_a_success_status__without_property_set(self):
        statuses = ["INVITED", "ACTIVE", "UNLISTED", "INNACTIVE"]
        valid_statuses = ["ACTIVE", "UNLISTED"]

        for db_status in statuses:
            mentor_profile = {"status": db_status}
            model = self.bc.database.create(
                user=1,
                role=1,
                academy=1,
                capability="crud_mentorship_mentor",
                mentorship_service=1,
                profile_academy=1,
                mentor_profile=mentor_profile,
            )

            self.bc.request.set_headers(academy=model.academy.id)
            self.client.force_authenticate(model.user)

            url = reverse_lazy("mentorship:academy_mentor_id", kwargs={"mentor_id": model.mentor_profile.id})

            good_statuses = [x for x in statuses if x != db_status and x in valid_statuses]
            for current_status in good_statuses:
                model.mentor_profile.status = db_status
                model.mentor_profile.save()

                data = {"status": current_status}
                response = self.client.put(url, data)

                json = response.json()
                expected = {"detail": "without-first-name", "status_code": 400}

                self.assertEqual(json, expected)
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertEqual(
                    self.bc.database.list_of("mentorship.MentorProfile"),
                    [
                        self.bc.format.to_dict(model.mentor_profile),
                    ],
                )

                self.assertEqual(actions.mentor_is_ready.call_args_list, [])

                # teardown
                actions.mentor_is_ready.call_args_list = []

            # teardown
            self.bc.database.delete("mentorship.MentorProfile")

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__post__creating_a_elements_without_name(self):
        email = self.bc.fake.email()
        profile_academy = {"name": self.bc.fake.name(), "email": email}
        model = self.bc.database.create(
            user=1, role=1, capability="crud_mentorship_mentor", profile_academy=profile_academy, mentorship_service=1
        )

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_mentor")
        data = {"slug": "mirai-nikki", "price_per_hour": 20, "services": [1], "user": 1}
        response = self.client.post(url, data, format="json")

        json = response.json()
        expected = {"detail": "name-not-found", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__post__creating_a_elements_without_email(self):
        profile_academy = {
            "name": self.bc.fake.name(),
        }
        user = {"first_name": self.bc.fake.name(), "last_name": self.bc.fake.name(), "email": ""}
        model = self.bc.database.create(
            user=user,
            role=1,
            capability="crud_mentorship_mentor",
            profile_academy=profile_academy,
            mentorship_service=1,
        )

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_mentor")
        data = {"slug": "mirai-nikki", "price_per_hour": 20, "services": [1], "user": 1, "name": "Mirai Nikki"}
        response = self.client.post(url, data, format="json")

        json = response.json()
        expected = {"detail": "email-not-found", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
