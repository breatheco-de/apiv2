from unittest.mock import MagicMock, call, patch

from django.urls import reverse_lazy
from rest_framework import status

from breathecode.utils.api_view_extensions.extensions import lookup_extension
from ..mixins import PaymentsTestCase


def academy_serializer(academy):
    return {
        "id": academy.id,
        "name": academy.name,
        "slug": academy.slug,
    }


def mentorship_service_serializer(self, mentorship_service, academy):
    return {
        "academy": academy_serializer(academy),
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
    }


def get_serializer(self, mentorship_service_set, mentorship_services, academy):
    return {
        "id": mentorship_service_set.id,
        "slug": mentorship_service_set.slug,
        "academy": academy_serializer(academy),
        "mentorship_services": [
            mentorship_service_serializer(self, mentorship_service, academy)
            for mentorship_service in mentorship_services
        ],
    }


class SignalTestSuite(PaymentsTestCase):
    """
    🔽🔽🔽 GET without auth
    """

    # Given: 0 MentorshipServiceSet
    # When: get with no auth
    # Then: return 200
    def test__no_auth(self):
        url = reverse_lazy("payments:mentorshipserviceset")
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("payments.MentorshipServiceSet"), [])

    # Given: 2 MentorshipServiceSet, 2 MentorshipService and 1 Academy
    # When: get with no auth
    # Then: return 200 with 2 MentorshipServiceSet
    def test__two_items(self):
        model = self.bc.database.create(mentorship_service_set=2, mentorship_service=2)

        url = reverse_lazy("payments:mentorshipserviceset")
        response = self.client.get(url)

        json = response.json()
        expected = [
            get_serializer(
                self,
                model.mentorship_service_set[1],
                [model.mentorship_service[0], model.mentorship_service[1]],
                model.academy,
            ),
            get_serializer(
                self,
                model.mentorship_service_set[0],
                [model.mentorship_service[0], model.mentorship_service[1]],
                model.academy,
            ),
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("payments.MentorshipServiceSet"),
            self.bc.format.to_dict(model.mentorship_service_set),
        )

    # Given: compile_lookup was mocked
    # When: the mock is called
    # Then: the mock should be called with the correct arguments and does not raise an exception
    @patch(
        "breathecode.utils.api_view_extensions.extensions.lookup_extension.compile_lookup",
        MagicMock(wraps=lookup_extension.compile_lookup),
    )
    def test_lookup_extension(self):
        self.bc.request.set_headers(academy=1)

        model = self.bc.database.create(mentorship_service_set=2, mentorship_service=2)

        args, kwargs = self.bc.format.call(
            "en",
            slugs=[
                "",
                "academy",
                "mentorship_services",
            ],
            overwrite={
                "mentorship_service": "mentorship_services",
            },
        )

        query = self.bc.format.lookup(*args, **kwargs)
        url = reverse_lazy("payments:mentorshipserviceset") + "?" + self.bc.format.querystring(query)

        self.assertEqual([x for x in query], ["id", "slug", "academy", "mentorship_service"])

        response = self.client.get(url)

        json = response.json()
        expected = []

        for x in ["overwrite", "custom_fields"]:
            if x in kwargs:
                del kwargs[x]

        for field in ["ids", "slugs"]:
            values = kwargs.get(field, tuple())
            kwargs[field] = tuple(values)

        for field in ["ints", "strings", "bools", "datetimes"]:
            modes = kwargs.get(field, {})
            for mode in modes:
                if not isinstance(kwargs[field][mode], tuple):
                    kwargs[field][mode] = tuple(kwargs[field][mode])

            kwargs[field] = frozenset(modes.items())

        self.bc.check.calls(
            lookup_extension.compile_lookup.call_args_list,
            [
                call(**kwargs),
            ],
        )

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.bc.database.list_of("payments.MentorshipServiceSet"),
            self.bc.format.to_dict(model.mentorship_service_set),
        )
