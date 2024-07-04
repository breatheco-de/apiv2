"""
This file just can contains duck tests refert to AcademyInviteView
"""

from datetime import timedelta
from unittest.mock import MagicMock, call, patch

from django.urls.base import reverse_lazy
from rest_framework import status

from breathecode.utils.api_view_extensions.api_view_extension_handlers import APIViewExtensionHandlers

from ..mixins import MentorshipTestCase


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


def post_serializer(data={}):
    return {
        "allow_mentee_to_extend": True,
        "allow_mentors_to_extend": True,
        "description": None,
        "duration": "01:00:00",
        "id": 0,
        "language": "en",
        "logo_url": None,
        "max_duration": "02:00:00",
        "missed_meeting_duration": "00:10:00",
        "name": "",
        "slug": "",
        "status": "DRAFT",
        "video_provider": "GOOGLE_MEET",
        **data,
    }


def mentorship_service_columns(data={}):
    return {
        "academy_id": 0,
        "allow_mentee_to_extend": True,
        "allow_mentors_to_extend": True,
        "description": None,
        "duration": timedelta(seconds=3600),
        "id": 0,
        "language": "en",
        "logo_url": None,
        "max_duration": timedelta(seconds=7200),
        "missed_meeting_duration": timedelta(seconds=600),
        "name": "",
        "slug": "",
        "status": "DRAFT",
        "video_provider": "GOOGLE_MEET",
        **data,
    }


class AcademyServiceTestSuite(MentorshipTestCase):
    """
    🔽🔽🔽 Auth
    """

    def test__get__without_auth(self):
        url = reverse_lazy("mentorship:academy_service")
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

        url = reverse_lazy("mentorship:academy_service")
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

        url = reverse_lazy("mentorship:academy_service")
        response = self.client.get(url)

        json = response.json()
        expected = {
            "detail": "You (user: 1) don't have this capability: read_mentorship_service for academy 1",
            "status_code": 403,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    """
    🔽🔽🔽 GET without data
    """

    def test__get__without_data(self):
        model = self.bc.database.create(user=1, role=1, capability="read_mentorship_service", profile_academy=1)

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_service")
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    """
    🔽🔽🔽 GET with one MentorshipService
    """

    def test__get__with_one_mentorship_service(self):
        model = self.bc.database.create(
            user=1, role=1, capability="read_mentorship_service", mentorship_service=1, profile_academy=1
        )

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_service")
        response = self.client.get(url)

        json = response.json()
        expected = [
            get_serializer(self, model.mentorship_service, model.academy),
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipService"),
            [
                self.bc.format.to_dict(model.mentorship_service),
            ],
        )

    """
    🔽🔽🔽 GET with two MentorshipService
    """

    def test__get__with_two_mentorship_service(self):
        model = self.bc.database.create(
            user=1, role=1, capability="read_mentorship_service", mentorship_service=2, profile_academy=1
        )

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_service")
        response = self.client.get(url)

        json = response.json()
        mentorship_service = sorted(model.mentorship_service, key=lambda x: x.created_at, reverse=True)
        expected = [
            get_serializer(self, mentorship_service[0], model.academy),
            get_serializer(self, mentorship_service[1], model.academy),
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipService"), self.bc.format.to_dict(model.mentorship_service)
        )

    """
    🔽🔽🔽 GET with two MentorshipService passing status in querystring
    """

    def test__get__with_two_mentorship_service__passing_bad_status(self):
        statuses = ["DRAFT", "ACTIVE", "UNLISTED", "INNACTIVE"]

        for n in range(0, 3):
            # 0, 1, 10, 11, 0
            current_bin_key = bin(n).replace("0b", "")[-2:]
            current_key = int(current_bin_key, 2)
            current_status = statuses[current_key]

            # 0, 1, 10, 11, 0
            bad_bin_key = bin(n + 1).replace("0b", "")[-2:]
            bad_key = int(bad_bin_key, 2)
            bad_status = statuses[bad_key]

            mentorship_service = {"status": current_status}
            model = self.bc.database.create(
                user=1,
                role=1,
                capability="read_mentorship_service",
                mentorship_service=(2, mentorship_service),
                profile_academy=1,
            )

            self.bc.request.set_headers(academy=model.academy.id)
            self.client.force_authenticate(model.user)

            url = reverse_lazy("mentorship:academy_service") + f"?status={bad_status}"
            response = self.client.get(url)

            json = response.json()
            expected = []

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(
                self.bc.database.list_of("mentorship.MentorshipService"),
                self.bc.format.to_dict(model.mentorship_service),
            )

            self.bc.database.delete("mentorship.MentorshipService")

    def test__get__with_two_mentorship_service__passing_status(self):
        statuses = ["DRAFT", "ACTIVE", "UNLISTED", "INNACTIVE"]

        for current_status in statuses:
            mentorship_service = {"status": current_status}
            model = self.bc.database.create(
                user=1,
                role=1,
                capability="read_mentorship_service",
                mentorship_service=(2, mentorship_service),
                profile_academy=1,
            )

            self.bc.request.set_headers(academy=model.academy.id)
            self.client.force_authenticate(model.user)

            url = reverse_lazy("mentorship:academy_service") + f"?status={current_status}"
            response = self.client.get(url)

            json = response.json()
            mentorship_service = sorted(model.mentorship_service, key=lambda x: x.created_at, reverse=True)
            expected = [
                get_serializer(self, mentorship_service[0], model.academy, data={"status": current_status}),
                get_serializer(self, mentorship_service[1], model.academy, data={"status": current_status}),
            ]

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(
                self.bc.database.list_of("mentorship.MentorshipService"),
                self.bc.format.to_dict(model.mentorship_service),
            )

            self.bc.database.delete("mentorship.MentorshipService")

    """
    🔽🔽🔽 GET passing name in querystring
    """

    def test__get__mentorship_service__passing_name_wrong(self):

        model = self.bc.database.create(
            user=1,
            role=1,
            capability="read_mentorship_service",
            mentorship_service=[{"name": "first"}, {"name": "second"}],
            profile_academy=1,
        )

        self.bc.request.set_headers(academy=model.academy.id)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_service") + f"?name=g"
        response = self.client.get(url)

        json = response.json()
        mentorship_service = sorted(model.mentorship_service, key=lambda x: x.created_at, reverse=True)
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipService"),
            self.bc.format.to_dict(model.mentorship_service),
        )

        self.bc.database.delete("mentorship.MentorshipService")

    def test__get__mentorship_service__passing_name(self):

        model = self.bc.database.create(
            user=1,
            role=1,
            capability="read_mentorship_service",
            mentorship_service=[{"name": "first"}, {"name": "second"}],
            profile_academy=1,
        )

        self.bc.request.set_headers(academy=model.academy.id)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_service") + f"?name=f"
        response = self.client.get(url)

        json = response.json()
        mentorship_service = sorted(model.mentorship_service, key=lambda x: x.created_at, reverse=True)
        expected = [
            get_serializer(self, model.mentorship_service[0], model.academy),
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipService"),
            self.bc.format.to_dict(model.mentorship_service),
        )

        self.bc.database.delete("mentorship.MentorshipService")

    """
    🔽🔽🔽 Spy the extensions
    """

    @patch.object(APIViewExtensionHandlers, "_spy_extensions", MagicMock())
    @patch.object(APIViewExtensionHandlers, "_spy_extension_arguments", MagicMock())
    def test__get__spy_extensions(self):
        model = self.bc.database.create(user=1, role=1, capability="read_mentorship_service", profile_academy=1)

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_service")
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

        url = reverse_lazy("mentorship:academy_service")
        response = self.client.post(url)

        json = response.json()
        expected = {
            "detail": "You (user: 1) don't have this capability: crud_mentorship_service for academy 1",
            "status_code": 403,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    """
    🔽🔽🔽 POST without required fields in body
    """

    def test__post__without_required_fields_in_body(self):
        model = self.bc.database.create(user=1, role=1, capability="crud_mentorship_service", profile_academy=1)

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_service")
        response = self.client.post(url)

        json = response.json()
        expected = {"name": ["This field is required."], "slug": ["This field is required."]}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    """
    🔽🔽🔽 POST creating a element
    """

    def test__post__creating_a_element(self):
        model = self.bc.database.create(user=1, role=1, capability="crud_mentorship_service", profile_academy=1)

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("mentorship:academy_service")
        data = {"slug": "mirai-nikki", "name": "Mirai Nikki"}
        response = self.client.post(url, data, format="json")

        json = response.json()
        expected = post_serializer({**data, "id": 1})

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipService"),
            [
                mentorship_service_columns(
                    {
                        **data,
                        "id": 1,
                        "academy_id": 1,
                    }
                ),
            ],
        )

    """
    🔽🔽🔽 DELETE
    """

    def test_delete__service__without_lookups(self):
        self.headers(academy=1)

        model = self.generate_models(
            authenticate=True, role=1, capability="crud_event", profile_academy=1, mentorship_service=(2)
        )

        url = reverse_lazy("mentorship:academy_service")

        response = self.client.delete(url)
        json = response.json()
        expected = {"detail": "without-lookups-and-service-id", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipService"), self.bc.format.to_dict(model.mentorship_service)
        )

    def test_service__delete__can_delete(self):
        self.headers(academy=1)

        model = self.generate_models(
            authenticate=True, role=1, capability="crud_event", profile_academy=1, mentorship_service=(2)
        )

        url = (
            reverse_lazy("mentorship:academy_service")
            + f'?id={",".join([str(x.id) for x in model.mentorship_service])}'
        )

        response = self.client.delete(url)

        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.bc.database.list_of("mentorship.MentorshipService"), [])

    def test_service__delete__all_errors_and_success_cases(self):

        can_delete_services = [
            {
                "slug": self.bc.fake.slug(),
                "academy_id": 1,
            }
        ]
        services_from_other_academy = [
            {
                "academy_id": 2,
                "slug": self.bc.fake.slug(),
            },
            {
                "academy_id": 2,
                "slug": self.bc.fake.slug(),
            },
        ]
        services_with_mentor = [
            {
                "academy_id": 1,
                "slug": self.bc.fake.slug(),
            }
        ]
        services_with_session = [
            {
                "academy_id": 1,
                "slug": self.bc.fake.slug(),
            }
        ]
        services = can_delete_services + services_from_other_academy + services_with_mentor + services_with_session
        model = self.generate_models(
            user=1,
            role=1,
            academy=2,
            capability="crud_event",
            profile_academy=1,
            mentorship_service=services,
            mentor_profile={"slug": 1, "services": "4"},
            mentorship_session={"slug": 1, "service_id": 5},
        )

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = (
            reverse_lazy("mentorship:academy_service")
            + f'?id={",".join([str(x.id) for x in model.mentorship_service])}'
        )

        response = self.client.delete(url)
        json = response.json()
        expected = {
            "success": [
                {
                    "status_code": 204,
                    "resources": [
                        {
                            "pk": model.mentorship_service[0].id,
                            "display_field": "slug",
                            "display_value": model.mentorship_service[0].slug,
                        }
                    ],
                }
            ],
            "failure": [
                {
                    "detail": "not-found",
                    "status_code": 400,
                    "resources": [
                        {
                            "pk": model.mentorship_service[1].id,
                            "display_field": "slug",
                            "display_value": model.mentorship_service[1].slug,
                        },
                        {
                            "pk": model.mentorship_service[2].id,
                            "display_field": "slug",
                            "display_value": model.mentorship_service[2].slug,
                        },
                    ],
                },
                {
                    "detail": "service-with-mentor",
                    "status_code": 400,
                    "resources": [
                        {
                            "pk": model.mentorship_service[3].id,
                            "display_field": "slug",
                            "display_value": model.mentorship_service[3].slug,
                        }
                    ],
                },
                {
                    "detail": "service-with-session",
                    "status_code": 400,
                    "resources": [
                        {
                            "pk": model.mentorship_service[4].id,
                            "display_field": "slug",
                            "display_value": model.mentorship_service[4].slug,
                        }
                    ],
                },
            ],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 207)
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipService"),
            self.bc.format.to_dict(model.mentorship_service[1:]),
        )
