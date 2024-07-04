"""
Test /v1/marketing/upload
"""

import csv
import hashlib
import json
import os
import random
import tempfile
from unittest.mock import MagicMock, Mock, PropertyMock, call, patch

import pandas as pd
from django.urls.base import reverse_lazy
from django.utils import dateparse, timezone
from rest_framework import status

from breathecode.marketing.views import MIME_ALLOW
from breathecode.provisioning import tasks
from breathecode.utils.api_view_extensions.api_view_extension_handlers import APIViewExtensionHandlers
from breathecode.utils.api_view_extensions.extensions import lookup_extension

from ..mixins import ProvisioningTestCase

UTC_NOW = timezone.now()


def format_field(x):
    if x is None:
        return ""

    return str(x)


HEADER = ",".join(
    [
        "amount",
        "id",
        "kind.id",
        "kind.product_name",
        "kind.sku",
        "processed_at",
        "quantity",
        "status",
        "username",
    ]
)


def format_csv(provisioning_activity, provisioning_user_kind):
    return ",".join(
        [
            format_field(float(provisioning_activity.amount)),
            format_field(provisioning_activity.id),
            format_field(provisioning_user_kind.id),
            format_field(provisioning_user_kind.product_name),
            format_field(provisioning_user_kind.sku),
            format_field(provisioning_activity.processed_at),
            format_field(float(provisioning_activity.quantity)),
            format_field(provisioning_activity.status),
            format_field(provisioning_activity.username),
        ]
    )


def provisioning_bill_serializer(self, provisioning_bill):
    return {
        "created_at": self.bc.datetime.to_iso_string(provisioning_bill.created_at),
        "fee": provisioning_bill.fee,
        "id": provisioning_bill.id,
        "paid_at": provisioning_bill.paid_at,
        "status": provisioning_bill.status,
        "status_details": provisioning_bill.status_details,
        "stripe_url": provisioning_bill.stripe_url,
        "total_amount": provisioning_bill.total_amount,
        "vendor": provisioning_bill.vendor,
    }


def provisioning_consumption_kind_serializer(provisioning_consumption_kind):
    return {
        "id": provisioning_consumption_kind.id,
        "product_name": provisioning_consumption_kind.product_name,
        "sku": provisioning_consumption_kind.sku,
    }


def get_serializer(self, provisioning_activity, provisioning_consumption_kind):
    return {
        # 'bills': [provisioning_bill_serializer(self, x) for x in provisioning_bills],
        "kind": provisioning_consumption_kind_serializer(provisioning_consumption_kind),
        "id": provisioning_activity.id,
        "processed_at": provisioning_activity.processed_at,
        "amount": provisioning_activity.amount,
        "quantity": provisioning_activity.quantity,
        "status": provisioning_activity.status,
        "username": provisioning_activity.username,
    }


class MarketingTestSuite(ProvisioningTestCase):
    """Test /answer"""

    # When: no auth
    # Then: should return 401
    def test_upload_without_auth(self):

        self.headers(accept="application/json", content_disposition='attachment; filename="filename.csv"')

        url = reverse_lazy("provisioning:academy_userconsumption")

        response = self.client.get(url)
        json = response.json()
        expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # When: auth and no capability
    # Then: should return 403
    def test_upload_without_capability(self):

        model = self.bc.database.create(user=1)
        self.client.force_authenticate(model.user)

        self.headers(academy=1, accept="application/json", content_disposition='attachment; filename="filename.csv"')

        url = reverse_lazy("provisioning:academy_userconsumption")

        response = self.client.get(url)

        json = response.json()
        expected = {
            "detail": "You (user: 1) don't have this capability: read_provisioning_activity for academy 1",
            "status_code": 403,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # When: No activity
    # Then: Should return empty csv
    def test_no_activity(self):

        model = self.bc.database.create(user=1, profile_academy=1, role=1, capability="read_provisioning_activity")
        self.client.force_authenticate(model.user)

        self.headers(academy=1, accept="text/csv", content_disposition='attachment; filename="filename.csv"')

        url = reverse_lazy("provisioning:academy_userconsumption")

        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = ""

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("provisioning.ProvisioningUserConsumption"), [])

    # Given: 2 ProvisioningActivity and 1 ProvisioningBill
    # When: no filters
    # Then: Should return 2 rows
    def test__csv__activities(self):

        model = self.bc.database.create(
            user=1,
            profile_academy=1,
            role=1,
            capability="read_provisioning_activity",
            provisioning_user_consumption=2,
            provisioning_bill=1,
        )
        self.client.force_authenticate(model.user)

        self.headers(academy=1, accept="text/csv", content_disposition='attachment; filename="filename.csv"')

        url = reverse_lazy("provisioning:academy_userconsumption")

        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = "\r\n".join(
            [
                HEADER,
                format_csv(model.provisioning_user_consumption[1], model.provisioning_consumption_kind),
                format_csv(model.provisioning_user_consumption[0], model.provisioning_consumption_kind),
                "",
            ]
        )

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningUserConsumption"),
            self.bc.format.to_dict(model.provisioning_user_consumption),
        )

    # Given: 2 ProvisioningActivity and 1 ProvisioningBill
    # When: no filters
    # Then: Should return 2 rows
    def test__json__activities(self):

        model = self.bc.database.create(
            user=1,
            profile_academy=1,
            role=1,
            capability="read_provisioning_activity",
            provisioning_user_consumption=2,
            provisioning_bill=1,
        )
        self.client.force_authenticate(model.user)

        self.headers(academy=1, accept="application/json", content_disposition='attachment; filename="filename.csv"')

        url = reverse_lazy("provisioning:academy_userconsumption")

        response = self.client.get(url)

        json = response.json()
        expected = [
            get_serializer(self, model.provisioning_user_consumption[1], model.provisioning_consumption_kind),
            get_serializer(self, model.provisioning_user_consumption[0], model.provisioning_consumption_kind),
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningUserConsumption"),
            self.bc.format.to_dict(model.provisioning_user_consumption),
        )

    # Given: compile_lookup was mocked
    # When: the mock is called
    # Then: the mock should be called with the correct arguments and does not raise an exception
    @patch(
        "breathecode.utils.api_view_extensions.extensions.lookup_extension.compile_lookup",
        MagicMock(wraps=lookup_extension.compile_lookup),
    )
    def test_lookup_extension(self):
        self.bc.request.set_headers(academy=1, accept="application/json")

        model = self.bc.database.create(
            user=1,
            profile_academy=1,
            role=1,
            capability="read_provisioning_activity",
            provisioning_user_consumption=2,
            provisioning_bill=1,
        )

        self.client.force_authenticate(model.user)

        args, kwargs = self.bc.format.call(
            "en",
            strings={
                "iexact": [
                    "hash",
                    "username",
                    "status",
                    "kind__product_name",
                    "kind__sku",
                ],
            },
            datetimes={
                "gte": ["processed_at"],
                "lte": ["created_at"],  # fix it
            },
            overwrite={
                "start": "processed_at",
                "end": "created_at",
                "product_name": "kind__product_name",
                "sku": "kind__sku",
            },
        )

        query = self.bc.format.lookup(*args, **kwargs)
        url = reverse_lazy("provisioning:academy_userconsumption") + "?" + self.bc.format.querystring(query)

        self.assertEqual([x for x in query], ["hash", "username", "status", "product_name", "sku", "start", "end"])

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
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningUserConsumption"),
            self.bc.format.to_dict(model.provisioning_user_consumption),
        )

    # When: get is called
    # Then: it's setup properly
    @patch.object(APIViewExtensionHandlers, "_spy_extensions", MagicMock())
    @patch.object(APIViewExtensionHandlers, "_spy_extension_arguments", MagicMock())
    def test_get__spy_extensions(self):
        model = self.bc.database.create(
            user=1,
            profile_academy=1,
            role=1,
            capability="read_provisioning_activity",
            provisioning_user_consumption=2,
            provisioning_bill=1,
        )

        self.bc.request.set_headers(academy=1, accept="application/json")
        self.client.force_authenticate(model.user)

        url = reverse_lazy("provisioning:academy_userconsumption")
        self.client.get(url)

        self.bc.check.calls(
            APIViewExtensionHandlers._spy_extensions.call_args_list,
            [
                call(["LanguageExtension", "LookupExtension", "SortExtension"]),
            ],
        )

        self.bc.check.calls(
            APIViewExtensionHandlers._spy_extension_arguments.call_args_list,
            [
                call(sort="-id"),
            ],
        )
