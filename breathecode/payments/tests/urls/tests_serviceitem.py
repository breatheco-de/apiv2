import math
import random
from datetime import timedelta
from unittest.mock import MagicMock, call, patch

from django.urls import reverse_lazy
from django.utils import timezone
from rest_framework import status
from rest_framework.authtoken.models import Token

from breathecode.payments import signals

from ..mixins import PaymentsTestCase

UTC_NOW = timezone.now()


def format_user_setting(data={}):
    return {
        "id": 1,
        "user_id": 1,
        "main_currency_id": None,
        "lang": "en",
        **data,
    }


def format_invoice_item(data={}):
    return {
        "academy_id": None,
        "amount": 0.0,
        "currency_id": 1,
        "bag_id": None,
        "id": 1,
        "paid_at": UTC_NOW,
        "status": "FULFILLED",
        "stripe_id": None,
        "user_id": 1,
        **data,
    }


def feature_serializer(service_item_feature):
    return {
        "description": service_item_feature.description,
        "one_line_desc": service_item_feature.one_line_desc,
        "title": service_item_feature.title,
    }


def get_serializer(service_item, service, service_item_features=[], data={}):
    features = [feature_serializer(service_item_feature) for service_item_feature in service_item_features]
    return {
        "features": features,
        "how_many": service_item.how_many,
        "service": {
            "groups": [],
            "private": service.private,
            "slug": service.slug,
            "title": service.title,
            "icon_url": service.icon_url,
        },
        "unit_type": service_item.unit_type,
        "sort_priority": service_item.sort_priority,
        **data,
    }


class SignalTestSuite(PaymentsTestCase):
    """
    🔽🔽🔽 GET without auth
    """

    def test__without_auth__without_service_items(self):
        url = reverse_lazy("payments:serviceitem")
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("payments.ServiceItem"), [])

    def test__without_auth__with_service_items(self):
        service_item_features = [{"lang": "en", "service_item_id": 1} for _ in range(2)]
        service_item_features += [{"lang": "en", "service_item_id": 2} for _ in range(2)]
        plan_service_items = [{"service_item_id": n} for n in range(1, 3)]
        plan = {"is_renewable": False}

        model = self.bc.database.create(
            plan=plan,
            service=1,
            service_item=2,
            plan_service_item=plan_service_items,
            service_item_feature=service_item_features,
        )

        url = reverse_lazy("payments:serviceitem")
        response = self.client.get(url)

        json = response.json()
        expected = [
            get_serializer(
                model.service_item[1],
                model.service,
                [model.service_item_feature[2], model.service_item_feature[3]],
                data={},
            ),
            get_serializer(
                model.service_item[0],
                model.service,
                [model.service_item_feature[0], model.service_item_feature[1]],
                data={},
            ),
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("payments.ServiceItem"),
            self.bc.format.to_dict(model.service_item),
        )

    """
    🔽🔽🔽 Without auth filtering by lang
    """

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__without_auth__filtering_by_lang(self):
        service_item_features = [{"lang": "en", "service_item_id": 1} for _ in range(2)]
        service_item_features += [{"lang": "es", "service_item_id": 1} for _ in range(2)]
        plan = {"is_renewable": False}

        model = self.bc.database.create(
            plan=plan, service=1, service_item=1, plan_service_item=1, service_item_feature=service_item_features
        )

        url = reverse_lazy("payments:serviceitem")
        response = self.client.get(url)

        json = response.json()
        expected = [
            get_serializer(
                model.service_item,
                model.service,
                [model.service_item_feature[0], model.service_item_feature[1]],
                data={},
            ),
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("payments.ServiceItem"),
            [
                self.bc.format.to_dict(model.service_item),
            ],
        )

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__without_auth__filtering_by_lang_from_headers(self):
        service_item_features = [{"lang": "en", "service_item_id": 1} for _ in range(2)]
        service_item_features += [{"lang": "es", "service_item_id": 1} for _ in range(2)]
        plan = {"is_renewable": False}

        model = self.bc.database.create(
            plan=plan, service=1, service_item=1, plan_service_item=1, service_item_feature=service_item_features
        )

        self.bc.request.set_headers(accept_language="es")

        url = reverse_lazy("payments:serviceitem")
        response = self.client.get(url)

        json = response.json()
        expected = [
            get_serializer(
                model.service_item,
                model.service,
                [model.service_item_feature[2], model.service_item_feature[3]],
                data={},
            ),
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("payments.ServiceItem"),
            [
                self.bc.format.to_dict(model.service_item),
            ],
        )

    """
    🔽🔽🔽 Without auth filtering by plan
    """

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__without_auth__filtering_by_plan(self):
        service_item_features = [{"lang": "en", "service_item_id": n} for n in range(1, 5)]
        plan_service_items = [{"service_item_id": n} for n in range(1, 3)]
        plan = {"is_renewable": False}

        model = self.bc.database.create(
            plan=plan,
            service=1,
            service_item=4,
            plan_service_item=plan_service_items,
            service_item_feature=service_item_features,
        )

        url = reverse_lazy("payments:serviceitem") + "?plan=1"
        response = self.client.get(url)

        json = response.json()
        expected = [
            get_serializer(model.service_item[1], model.service, [model.service_item_feature[1]], data={}),
            get_serializer(model.service_item[0], model.service, [model.service_item_feature[0]], data={}),
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("payments.ServiceItem"),
            self.bc.format.to_dict(model.service_item),
        )

    """
    🔽🔽🔽 With auth
    """

    def test__with_auth__without_service_items(self):
        model = self.bc.database.create(user=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:serviceitem")
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("payments.ServiceItem"), [])

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__with_auth__with_service_items(self):
        service_item_features = [{"lang": "en", "service_item_id": 1} for _ in range(2)]
        service_item_features += [{"lang": "en", "service_item_id": 2} for _ in range(2)]
        plan_service_items = [{"service_item_id": n} for n in range(1, 3)]
        plan = {"is_renewable": False}

        model = self.bc.database.create(
            user=1,
            plan=plan,
            service=1,
            service_item=2,
            plan_service_item=plan_service_items,
            service_item_feature=service_item_features,
        )

        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:serviceitem")
        response = self.client.get(url)

        json = response.json()
        expected = [
            get_serializer(
                model.service_item[1],
                model.service,
                [model.service_item_feature[2], model.service_item_feature[3]],
                data={},
            ),
            get_serializer(
                model.service_item[0],
                model.service,
                [model.service_item_feature[0], model.service_item_feature[1]],
                data={},
            ),
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("payments.ServiceItem"),
            self.bc.format.to_dict(model.service_item),
        )

    """
    🔽🔽🔽 With auth filtering by lang
    """

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__with_auth__filtering_by_lang(self):
        service_item_features = [{"lang": "en", "service_item_id": 1} for _ in range(2)]
        service_item_features += [{"lang": "es", "service_item_id": 1} for _ in range(2)]
        plan = {"is_renewable": False}

        model = self.bc.database.create(
            user=1,
            plan=plan,
            service=1,
            service_item=1,
            plan_service_item=1,
            service_item_feature=service_item_features,
        )

        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:serviceitem")
        response = self.client.get(url)

        json = response.json()
        expected = [
            get_serializer(
                model.service_item,
                model.service,
                [model.service_item_feature[0], model.service_item_feature[1]],
                data={},
            ),
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("payments.ServiceItem"),
            [
                self.bc.format.to_dict(model.service_item),
            ],
        )

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__with_auth__filtering_by_lang_from_headers(self):
        service_item_features = [{"lang": "en", "service_item_id": 1} for _ in range(2)]
        service_item_features += [{"lang": "es", "service_item_id": 1} for _ in range(2)]
        plan = {"is_renewable": False}

        model = self.bc.database.create(
            user=1,
            plan=plan,
            service=1,
            service_item=1,
            plan_service_item=1,
            service_item_feature=service_item_features,
        )

        self.bc.request.set_headers(accept_language="es")
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:serviceitem")
        response = self.client.get(url)

        json = response.json()
        expected = [
            get_serializer(
                model.service_item,
                model.service,
                [model.service_item_feature[2], model.service_item_feature[3]],
                data={},
            ),
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("payments.ServiceItem"),
            [
                self.bc.format.to_dict(model.service_item),
            ],
        )

    """
    🔽🔽🔽 With auth filtering by plan
    """

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__with_auth__filtering_by_plan(self):
        service_item_features = [{"lang": "en", "service_item_id": n} for n in range(1, 5)]
        plan_service_items = [{"service_item_id": n} for n in range(1, 3)]
        plan = {"is_renewable": False}

        model = self.bc.database.create(
            user=1,
            plan=plan,
            service=1,
            service_item=4,
            plan_service_item=plan_service_items,
            service_item_feature=service_item_features,
        )

        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:serviceitem") + "?plan=1"
        response = self.client.get(url)

        json = response.json()
        expected = [
            get_serializer(model.service_item[1], model.service, [model.service_item_feature[1]], data={}),
            get_serializer(model.service_item[0], model.service, [model.service_item_feature[0]], data={}),
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("payments.ServiceItem"),
            self.bc.format.to_dict(model.service_item),
        )
