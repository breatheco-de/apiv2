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


def service_serializer(service):
    return {
        "groups": [],
        "private": service.private,
        "slug": service.slug,
        "title": service.title,
        "icon_url": service.icon_url,
    }


def currency_serializer(currency):
    return {
        "code": currency.code,
        "name": currency.name,
    }


def academy_service_serialize(academy_service, academy, currency, service):
    return {
        "academy": academy_serializer(academy),
        "currency": currency_serializer(currency),
        "id": academy_service.id,
        "max_items": academy_service.max_items,
        "bundle_size": academy_service.bundle_size,
        "max_amount": academy_service.max_amount,
        "discount_ratio": academy_service.discount_ratio,
        "price_per_unit": academy_service.price_per_unit,
        "service": service_serializer(service),
    }


def get_serializer(self, mentorship_service_set, mentorship_services, academy, academy_services, currency, service):
    return {
        "academy_services": [
            academy_service_serialize(academy_service, academy, currency, service)
            for academy_service in academy_services
        ],
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
    # Then: return 404
    def test__no_auth(self):
        url = reverse_lazy("payments:mentorshipserviceset_id", kwargs={"mentorship_service_set_id": 1})
        response = self.client.get(url)

        json = response.json()
        expected = {"detail": "not-found", "status_code": 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.bc.database.list_of("payments.MentorshipServiceSet"), [])

    # Given: 1 MentorshipServiceSet, 2 MentorshipService, 1 Academy, 1 AcademyService, 1 Currency and 1
    # Service
    # When: get with no auth
    # Then: return 200 with 2 MentorshipServiceSet
    def test__two_items(self):
        model = self.bc.database.create(mentorship_service_set=1, mentorship_service=2, academy_service=1)

        url = reverse_lazy("payments:mentorshipserviceset_id", kwargs={"mentorship_service_set_id": 1})
        response = self.client.get(url)

        json = response.json()
        expected = get_serializer(
            self,
            model.mentorship_service_set,
            [model.mentorship_service[0], model.mentorship_service[1]],
            model.academy,
            [model.academy_service],
            model.currency,
            model.service,
        )

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("payments.MentorshipServiceSet"),
            [
                self.bc.format.to_dict(model.mentorship_service_set),
            ],
        )
