"""
This file just can contains duck tests refert to AcademyInviteView
"""

import hashlib
from datetime import timedelta
from random import choices, random
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
                "description": mentorship_service.description,
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
        "syllabus": [],
        "updated_at": self.bc.datetime.to_iso_string(mentor_profile.updated_at),
        "user": {
            "email": user.email,
            "first_name": user.first_name,
            "id": user.id,
            "last_name": user.last_name,
        },
        **data,
    }


def put_serializer(self, mentor_profile, mentorship_service, user, syllabus=[], data={}):
    return {
        "id": mentor_profile.id,
        "one_line_bio": mentor_profile.one_line_bio,
        "slug": mentor_profile.slug,
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
        "status": mentor_profile.status,
        "price_per_hour": mentor_profile.price_per_hour,
        "rating": mentor_profile.rating,
        "booking_url": mentor_profile.booking_url,
        "online_meeting_url": mentor_profile.online_meeting_url,
        "timezone": mentor_profile.timezone,
        "syllabus": [{"id": x.id, "logo": x.logo, "name": x.name, "slug": x.slug} for x in syllabus],
        "email": mentor_profile.email,
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
        "online_meeting_url": None,
        "price_per_hour": 0,
        "service_id": 0,
        "slug": "mirai-nikki",
        "status": "INVITED",
        "timezone": None,
        "token": token,
        "user_id": 0,
        **data,
    }


class AcademyServiceTestSuite(MentorshipTestCase):
    """
    🔽🔽🔽 Auth
    """

    def test__get__without_auth(self):
        url = reverse_lazy("mentorship:academy_mentor_id", kwargs={"mentor_id": 1})
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

        url = reverse_lazy("mentorship:academy_mentor_id", kwargs={"mentor_id": 1})
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

        url = reverse_lazy("mentorship:academy_mentor_id", kwargs={"mentor_id": 1})
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

        url = reverse_lazy("mentorship:academy_mentor_id", kwargs={"mentor_id": 1})
        response = self.client.get(url)

        json = response.json()
        expected = {"detail": "This mentor does not exist on this academy", "status_code": 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

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

        url = reverse_lazy("mentorship:academy_mentor_id", kwargs={"mentor_id": 1})
        response = self.client.get(url)

        json = response.json()
        expected = get_serializer(self, model.mentor_profile, model.mentorship_service, model.user)

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorProfile"),
            [
                self.bc.format.to_dict(model.mentor_profile),
            ],
        )

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

        url = reverse_lazy("mentorship:academy_mentor_id", kwargs={"mentor_id": 1})
        self.client.get(url)

        self.assertEqual(
            APIViewExtensionHandlers._spy_extensions.call_args_list,
            [
                call(
                    ["CacheExtension", "LanguageExtension", "LookupExtension", "PaginationExtension", "SortExtension"]
                ),
            ],
        )

        self.assertEqual(
            APIViewExtensionHandlers._spy_extension_arguments.call_args_list,
            [
                call(cache=MentorProfileCache, sort="-created_at", paginate=True),
            ],
        )

    """
    🔽🔽🔽 PUT capability
    """

    def test__post__without_capabilities(self):
        model = self.bc.database.create(user=1)

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_mentor_id", kwargs={"mentor_id": 1})
        response = self.client.put(url)

        json = response.json()
        expected = {
            "detail": "You (user: 1) don't have this capability: crud_mentorship_mentor for academy 1",
            "status_code": 403,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    """
    🔽🔽🔽 PUT MentorProfile not found
    """

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("breathecode.mentorship.actions.mentor_is_ready", MagicMock())
    def test__post__not_found(self):
        model = self.bc.database.create(user=1, role=1, capability="crud_mentorship_mentor", profile_academy=1)

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_mentor_id", kwargs={"mentor_id": 1})
        response = self.client.put(url)

        json = response.json()
        expected = {"detail": "not-found", "status_code": 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.bc.database.list_of("mentorship.MentorProfile"), [])

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("breathecode.mentorship.actions.mentor_is_ready", MagicMock())
    def test__post__not_found__belong_to_another_academy(self):
        mentorship_service = {"academy_id": 2}
        model = self.bc.database.create(
            user=1,
            role=1,
            academy=2,
            capability="crud_mentorship_mentor",
            mentorship_service=mentorship_service,
            profile_academy=1,
            mentor_profile=1,
        )

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_mentor_id", kwargs={"mentor_id": 1})
        response = self.client.put(url)

        json = response.json()
        expected = {"detail": "not-found", "status_code": 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorProfile"),
            [
                self.bc.format.to_dict(model.mentor_profile),
            ],
        )

    """
    🔽🔽🔽 PUT with one MentorProfile
    """

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("breathecode.mentorship.actions.mentor_is_ready", MagicMock())
    def test__post__with_one_mentor_profile(self):
        profile_academy = {
            "first_name": self.bc.fake.name(),
            "last_name": self.bc.fake.name(),
            "email": self.bc.fake.email(),
        }
        model = self.bc.database.create(
            user=1,
            role=1,
            academy=1,
            capability="crud_mentorship_mentor",
            mentorship_service=1,
            profile_academy=profile_academy,
            mentor_profile=1,
        )

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_mentor_id", kwargs={"mentor_id": 1})
        response = self.client.put(url)

        json = response.json()
        expected = put_serializer(
            self,
            model.mentor_profile,
            model.mentorship_service,
            model.user,
            data={"email": model.profile_academy.email},
        )

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorProfile"),
            [
                {
                    **self.bc.format.to_dict(model.mentor_profile),
                    "email": model.profile_academy.email,
                    "name": model.profile_academy.first_name + " " + model.profile_academy.last_name,
                }
            ],
        )

    """
    🔽🔽🔽 PUT with one MentorProfile passing readonly fields
    """

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("breathecode.mentorship.actions.mentor_is_ready", MagicMock())
    def test__post__with_one_mentor_profile__passing_randomly_fields(self):
        profile_academy = {
            "first_name": self.bc.fake.name(),
            "last_name": self.bc.fake.name(),
            "email": self.bc.fake.email(),
        }
        model = self.bc.database.create(
            user=1,
            role=1,
            academy=1,
            capability="crud_mentorship_mentor",
            mentorship_service=1,
            profile_academy=profile_academy,
            mentor_profile=1,
        )

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_mentor_id", kwargs={"mentor_id": 1})

        cases = ["user", "token"]
        for case in cases:
            data = {case: 1}
            response = self.client.put(url, data)

            json = response.json()
            expected = {"detail": f"{case}-read-only", "status_code": 400}

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(
                self.bc.database.list_of("mentorship.MentorProfile"),
                [
                    self.bc.format.to_dict(model.mentor_profile),
                ],
            )

    """
    🔽🔽🔽 PUT with one MentorProfile changing to a success status
    """

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("breathecode.mentorship.actions.mentor_is_ready", MagicMock())
    def test__post__with_one_mentor_profile__changing_to_a_success_status(self):
        statuses = ["INVITED", "ACTIVE", "UNLISTED", "INNACTIVE"]
        valid_statuses = ["ACTIVE", "UNLISTED"]
        profile_academy = {
            "first_name": self.bc.fake.name(),
            "last_name": self.bc.fake.name(),
            "email": self.bc.fake.email(),
        }
        for db_status in statuses:
            mentor_profile = {"status": db_status}
            model = self.bc.database.create(
                user=1,
                role=1,
                academy=1,
                capability="crud_mentorship_mentor",
                mentorship_service=1,
                profile_academy=profile_academy,
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
                expected = put_serializer(
                    self,
                    model.mentor_profile,
                    model.mentorship_service,
                    model.user,
                    data={"email": model.profile_academy.email, "status": current_status},
                )

                self.assertEqual(json, expected)
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(
                    self.bc.database.list_of("mentorship.MentorProfile"),
                    [
                        {
                            **self.bc.format.to_dict(model.mentor_profile),
                            **data,
                            "email": model.profile_academy.email,
                            "name": model.profile_academy.first_name + " " + model.profile_academy.last_name,
                        }
                    ],
                )
                self.assertEqual(actions.mentor_is_ready.call_args_list, [call(model.mentor_profile)])

                # teardown
                actions.mentor_is_ready.call_args_list = []

            # teardown
            self.bc.database.delete("mentorship.MentorProfile")

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("breathecode.mentorship.actions.mentor_is_ready", MagicMock(side_effect=Exception("hello")))
    def test__post__with_one_mentor_profile__changing_to_a_success_status__raise_a_exception(self):
        statuses = ["INVITED", "ACTIVE", "UNLISTED", "INNACTIVE"]
        valid_statuses = ["ACTIVE", "UNLISTED"]
        profile_academy = {
            "first_name": self.bc.fake.name(),
            "last_name": self.bc.fake.name(),
            "email": self.bc.fake.email(),
        }
        for db_status in statuses:
            mentor_profile = {"status": db_status}
            model = self.bc.database.create(
                user=1,
                role=1,
                academy=1,
                capability="crud_mentorship_mentor",
                mentorship_service=1,
                profile_academy=profile_academy,
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
                expected = {"detail": "hello", "status_code": 400}

                self.assertEqual(json, expected)
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertEqual(
                    self.bc.database.list_of("mentorship.MentorProfile"),
                    [
                        self.bc.format.to_dict(model.mentor_profile),
                    ],
                )

                self.assertEqual(actions.mentor_is_ready.call_args_list, [call(model.mentor_profile)])

                # teardown
                actions.mentor_is_ready.call_args_list = []

            # teardown
            self.bc.database.delete("mentorship.MentorProfile")

    """
    🔽🔽🔽 PUT with one MentorProfile changing to a failure status
    """

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("breathecode.mentorship.actions.mentor_is_ready", MagicMock())
    def test__post__with_one_mentor_profile__changing_to_a_failure_status(self):
        statuses = ["INVITED", "ACTIVE", "UNLISTED", "INNACTIVE"]
        valid_statuses = ["ACTIVE", "UNLISTED"]
        profile_academy = {
            "first_name": self.bc.fake.name(),
            "last_name": self.bc.fake.name(),
            "email": self.bc.fake.email(),
        }
        for db_status in statuses:
            mentor_profile = {"status": db_status}
            model = self.bc.database.create(
                user=1,
                role=1,
                academy=1,
                capability="crud_mentorship_mentor",
                mentorship_service=1,
                profile_academy=profile_academy,
                mentor_profile=mentor_profile,
            )

            self.bc.request.set_headers(academy=model.academy.id)
            self.client.force_authenticate(model.user)

            url = reverse_lazy("mentorship:academy_mentor_id", kwargs={"mentor_id": model.profile_academy.id})

            good_statuses = [x for x in statuses if x != db_status and x not in valid_statuses]
            for current_status in good_statuses:
                model.mentor_profile.status = db_status
                model.mentor_profile.save()

                data = {"status": current_status}
                response = self.client.put(url, data)

                json = response.json()
                expected = put_serializer(
                    self,
                    model.mentor_profile,
                    model.mentorship_service,
                    model.user,
                    data={"status": current_status, "email": model.profile_academy.email},
                )

                self.assertEqual(json, expected)
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(
                    self.bc.database.list_of("mentorship.MentorProfile"),
                    [
                        {
                            **self.bc.format.to_dict(model.mentor_profile),
                            "status": current_status,
                            "email": model.profile_academy.email,
                            "name": model.profile_academy.first_name + " " + model.profile_academy.last_name,
                        }
                    ],
                )

                self.assertEqual(actions.mentor_is_ready.call_args_list, [])

                # teardown
                actions.mentor_is_ready.call_args_list = []

            # teardown
            self.bc.database.delete("mentorship.MentorProfile")

    """
    🔽🔽🔽 PUT with one MentorProfile changing all the values
    """

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("breathecode.mentorship.actions.mentor_is_ready", MagicMock())
    def test__post__with_one_mentor_profile__changing_all_the_values(self):
        bad_statuses = ["INVITED", "INNACTIVE"]
        profile_academy = {
            "first_name": self.bc.fake.name(),
            "last_name": self.bc.fake.name(),
            "email": self.bc.fake.email(),
        }

        model = self.bc.database.create(
            user=1,
            role=1,
            academy=1,
            capability="crud_mentorship_mentor",
            mentorship_service=2,
            syllabus=2,
            profile_academy=profile_academy,
            mentor_profile=1,
        )

        self.bc.request.set_headers(academy=model.academy.id)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_mentor_id", kwargs={"mentor_id": model.mentor_profile.id})

        name = self.bc.fake.name()
        bio = self.bc.fake.text()
        data = {
            "status": choices(bad_statuses)[0],
            "slug": self.bc.fake.slug(),
            "name": name,
            "bio": bio,
            "email": self.bc.fake.email(),
            "booking_url": self.bc.fake.url(),
            "online_meeting_url": self.bc.fake.url(),
            "timezone": self.bc.fake.name(),
            "price_per_hour": random() * 100,
            "services": [2],
            "syllabus": [2],
        }
        response = self.client.put(url, data, format="json")

        json = response.json()

        del data["services"]
        del data["syllabus"]
        del data["bio"]
        del data["name"]

        expected = put_serializer(
            self, model.mentor_profile, model.mentorship_service[1], model.user, [model.syllabus[1]], data=data
        )

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorProfile"),
            [
                {
                    **self.bc.format.to_dict(model.mentor_profile),
                    **data,
                    "name": name,
                    "bio": bio,
                }
            ],
        )

        self.bc.check.queryset_with_pks(model.mentor_profile.services.all(), [2])

        self.assertEqual(actions.mentor_is_ready.call_args_list, [])

    """
    🔽🔽🔽 Post

    """

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("breathecode.mentorship.actions.mentor_is_ready", MagicMock())
    def test__post__with_one_mentor_without_profile_academy(self):

        model = self.bc.database.create(
            user=1,
            role=1,
            academy=1,
            capability="crud_mentorship_mentor",
            mentorship_service=1,
            profile_academy=1,
            mentor_profile=1,
        )

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_mentor_id", kwargs={"mentor_id": 1})
        response = self.client.put(url)

        json = response.json()
        expected = {"detail": "without-first-name", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("breathecode.mentorship.actions.mentor_is_ready", MagicMock())
    def test__post__with_one_mentor_without_last_name(self):
        profile_academy = {"first_name": self.bc.fake.name(), "email": self.bc.fake.email()}
        model = self.bc.database.create(
            user=1,
            role=1,
            academy=1,
            capability="crud_mentorship_mentor",
            mentorship_service=1,
            profile_academy=profile_academy,
            mentor_profile=1,
        )

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_mentor_id", kwargs={"mentor_id": 1})
        response = self.client.put(url)

        json = response.json()
        expected = {"detail": "without-last-name", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("breathecode.mentorship.actions.mentor_is_ready", MagicMock())
    def test__post__with_one_mentor_without_email(self):
        profile_academy = {"first_name": self.bc.fake.name(), "last_name": self.bc.fake.last_name()}
        model = self.bc.database.create(
            user=1,
            role=1,
            academy=1,
            capability="crud_mentorship_mentor",
            mentorship_service=1,
            profile_academy=profile_academy,
            mentor_profile=1,
        )

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_mentor_id", kwargs={"mentor_id": 1})
        response = self.client.put(url)

        json = response.json()
        expected = {"detail": "email-imposible-to-find", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("breathecode.mentorship.actions.mentor_is_ready", MagicMock())
    def test__post__with_one_mentor_profile_name_not_found(self):
        profile_academy = {"first_name": "", "last_name": "", "email": self.bc.fake.email()}
        user = {"first_name": "", "last_name": "", "email": self.bc.fake.email()}
        model = self.bc.database.create(
            user=user,
            role=1,
            academy=1,
            capability="crud_mentorship_mentor",
            mentorship_service=1,
            profile_academy=profile_academy,
            mentor_profile=1,
        )

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_mentor_id", kwargs={"mentor_id": 1})
        response = self.client.put(url)

        json = response.json()
        expected = {"detail": "without-first-name", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("breathecode.mentorship.actions.mentor_is_ready", MagicMock())
    def test__post__with_one_mentor_profile_with_only_first_name(self):
        profile_academy = {"first_name": self.bc.fake.first_name(), "last_name": "", "email": self.bc.fake.email()}
        user = {"first_name": self.bc.fake.first_name(), "last_name": "", "email": self.bc.fake.email()}
        model = self.bc.database.create(
            user=user,
            role=1,
            academy=1,
            capability="crud_mentorship_mentor",
            mentorship_service=1,
            profile_academy=profile_academy,
            mentor_profile=1,
        )

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_mentor_id", kwargs={"mentor_id": 1})
        response = self.client.put(url)

        json = response.json()
        expected = {"detail": "without-last-name", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
