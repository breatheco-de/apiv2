"""
This file just can contains duck tests refert to AcademyInviteView
"""

import random
from datetime import timedelta
from unittest.mock import MagicMock, call, patch

from django.urls.base import reverse_lazy
from django.utils import timezone
from rest_framework import status

from breathecode.utils.api_view_extensions.api_view_extension_handlers import APIViewExtensionHandlers

from ..mixins import MentorshipTestCase

UTC_NOW = timezone.now()


def get_serializer(self, mentorship_service, academy, data={}):
    return {
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
        "description": mentorship_service.description,
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
        **data,
    }


def put_serializer(self, mentorship_service, academy, data={}):
    return {
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
        "description": mentorship_service.description,
        "duration": self.bc.datetime.from_timedelta(mentorship_service.duration),
        "id": mentorship_service.id,
        "language": mentorship_service.language,
        "logo_url": mentorship_service.logo_url,
        "max_duration": self.bc.datetime.from_timedelta(mentorship_service.max_duration),
        "missed_meeting_duration": self.bc.datetime.from_timedelta(mentorship_service.missed_meeting_duration),
        "name": mentorship_service.name,
        "slug": mentorship_service.slug,
        "status": mentorship_service.status,
        "updated_at": self.bc.datetime.to_iso_string(UTC_NOW),
        **data,
    }


def mentorship_service_columns(mentorship_service, data={}):
    return {
        "academy_id": mentorship_service.academy_id,
        "allow_mentee_to_extend": mentorship_service.allow_mentee_to_extend,
        "allow_mentors_to_extend": mentorship_service.allow_mentors_to_extend,
        "description": mentorship_service.description,
        "duration": mentorship_service.duration,
        "id": mentorship_service.id,
        "language": mentorship_service.language,
        "logo_url": mentorship_service.logo_url,
        "max_duration": mentorship_service.max_duration,
        "missed_meeting_duration": mentorship_service.missed_meeting_duration,
        "name": mentorship_service.name,
        "slug": mentorship_service.slug,
        "status": mentorship_service.status,
        "video_provider": mentorship_service.video_provider,
        **data,
    }


class AcademyServiceTestSuite(MentorshipTestCase):
    """
    🔽🔽🔽 Auth
    """

    def test__get__without_auth(self):
        url = reverse_lazy("mentorship:academy_service_id", kwargs={"service_id": 1})
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

        url = reverse_lazy("mentorship:academy_service_id", kwargs={"service_id": 1})
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

        url = reverse_lazy("mentorship:academy_service_id", kwargs={"service_id": 1})
        response = self.client.get(url)

        json = response.json()
        expected = {
            "detail": "You (user: 1) don't have this capability: read_mentorship_service for academy 1",
            "status_code": 403,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    """
    🔽🔽🔽 GET MentorshipService not found
    """

    def test__get__without_data(self):
        model = self.bc.database.create(user=1, role=1, capability="read_mentorship_service", profile_academy=1)

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_service_id", kwargs={"service_id": 1})
        response = self.client.get(url)

        json = response.json()
        expected = {"detail": "not-found", "status_code": 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.bc.database.list_of("mentorship.MentorshipService"), [])

    """
    🔽🔽🔽 GET MentorshipService found
    """

    def test__get__with_one_mentorship_service(self):
        model = self.bc.database.create(
            user=1, role=1, capability="read_mentorship_service", mentorship_service=1, profile_academy=1
        )

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_service_id", kwargs={"service_id": 1})
        response = self.client.get(url)

        json = response.json()
        expected = get_serializer(self, model.mentorship_service, model.academy)

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipService"),
            [
                self.bc.format.to_dict(model.mentorship_service),
            ],
        )

    """
    🔽🔽🔽 Spy the extensions
    """

    @patch.object(APIViewExtensionHandlers, "_spy_extensions", MagicMock())
    @patch.object(APIViewExtensionHandlers, "_spy_extension_arguments", MagicMock())
    def test__get__spy_extensions(self):
        model = self.bc.database.create(user=1, role=1, capability="read_mentorship_service", profile_academy=1)

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_service_id", kwargs={"service_id": 1})
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

        url = reverse_lazy("mentorship:academy_service_id", kwargs={"service_id": 1})
        response = self.client.put(url)

        json = response.json()
        expected = {
            "detail": "You (user: 1) don't have this capability: crud_mentorship_service for academy 1",
            "status_code": 403,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    """
    🔽🔽🔽 PUT MentorshipService not found
    """

    def test__put__without_data(self):
        model = self.bc.database.create(user=1, role=1, capability="crud_mentorship_service", profile_academy=1)

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_service_id", kwargs={"service_id": 1})
        response = self.client.put(url)

        json = response.json()
        expected = {"detail": "not-found", "status_code": 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.bc.database.list_of("mentorship.MentorshipService"), [])

    """
    🔽🔽🔽 PUT MentorshipService found
    """

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__put__with_one_mentorship_service(self):
        model = self.bc.database.create(
            user=1, role=1, capability="crud_mentorship_service", mentorship_service=1, profile_academy=1
        )

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_service_id", kwargs={"service_id": 1})
        response = self.client.put(url)

        json = response.json()
        expected = put_serializer(self, model.mentorship_service, model.academy, data={})

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipService"),
            [
                self.bc.format.to_dict(model.mentorship_service),
            ],
        )

    """
    🔽🔽🔽 PUT MentorshipService found
    """

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__put__with_one_mentorship_service__passing_arguments(self):
        model = self.bc.database.create(
            user=1, role=1, capability="crud_mentorship_service", mentorship_service=1, profile_academy=1
        )

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_service_id", kwargs={"service_id": 1})
        data = {
            "name": self.bc.fake.name(),
            "logo_url": self.bc.fake.url(),
            "logo_url": self.bc.fake.url(),
            "allow_mentee_to_extend": bool(random.getrandbits(1)),
            "allow_mentors_to_extend": bool(random.getrandbits(1)),
            "language": "es",
            "status": random.choices(["DRAFT", "ACTIVE", "UNLISTED", "INNACTIVE"])[0],
            "description": self.bc.fake.text(),
        }
        response = self.client.put(url, data, format="json")

        json = response.json()
        expected = put_serializer(self, model.mentorship_service, model.academy, data=data)

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipService"),
            [
                mentorship_service_columns(model.mentorship_service, data),
            ],
        )
