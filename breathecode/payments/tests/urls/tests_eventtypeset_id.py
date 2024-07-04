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


def event_type_serializer(event_type, academy):
    return {
        # 'academy': academy_serializer(academy),
        "description": event_type.description,
        "lang": event_type.lang,
        "name": event_type.name,
        "id": event_type.id,
        "slug": event_type.slug,
        "icon_url": event_type.icon_url,
        "allow_shared_creation": event_type.allow_shared_creation,
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
        "price_per_unit": academy_service.price_per_unit,
        "max_items": academy_service.max_items,
        "bundle_size": academy_service.bundle_size,
        "max_amount": academy_service.max_amount,
        "discount_ratio": academy_service.discount_ratio,
        "service": service_serializer(service),
    }


def get_serializer(event_type_set, event_types, academy, academy_services, currency, service):
    return {
        "academy_services": [
            academy_service_serialize(academy_service, academy, currency, service)
            for academy_service in academy_services
        ],
        "id": event_type_set.id,
        "slug": event_type_set.slug,
        "academy": academy_serializer(academy),
        "event_types": [event_type_serializer(event_type, academy) for event_type in event_types],
    }


class SignalTestSuite(PaymentsTestCase):
    """
    🔽🔽🔽 GET without auth
    """

    # Given: 0 EventTypeSet
    # When: get with no auth
    # Then: return 404
    def test__no_auth(self):
        url = reverse_lazy("payments:eventtypeset_id", kwargs={"event_type_set_id": 1})
        response = self.client.get(url)

        json = response.json()
        expected = {"detail": "not-found", "status_code": 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.bc.database.list_of("payments.EventTypeSet"), [])

    # Given: 1 EventTypeSet, 2 EventType and 1 Academy, 1 AcademyService, 1 Currency and 1
    # Service
    # When: get with no auth
    # Then: return 200 with 1 EventTypeSet
    def test__one_item(self):
        event_types = [{"icon_url": self.bc.fake.url()} for _ in range(2)]
        model = self.bc.database.create(event_type_set=1, event_type=event_types, academy_service=1)

        url = reverse_lazy("payments:eventtypeset_id", kwargs={"event_type_set_id": 1})
        response = self.client.get(url)

        json = response.json()
        expected = get_serializer(
            model.event_type_set,
            [model.event_type[0], model.event_type[1]],
            model.academy,
            [model.academy_service],
            model.currency,
            model.service,
        )

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("payments.EventTypeSet"),
            [
                self.bc.format.to_dict(model.event_type_set),
            ],
        )
