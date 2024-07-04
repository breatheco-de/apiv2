"""
Test /v1/marketing/upload
"""

import random
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


def put_serializer(provisioning_bill, data={}):
    return {
        "status": provisioning_bill.status,
        **data,
    }


class MarketingTestSuite(ProvisioningTestCase):
    """Test /answer"""

    # When: no auth
    # Then: should return 401
    def test_upload_without_auth(self):

        self.headers(accept="application/json", content_disposition='attachment; filename="filename.csv"')

        url = reverse_lazy("provisioning:academy_bill_id", kwargs={"bill_id": 1})

        response = self.client.put(url)
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

        url = reverse_lazy("provisioning:academy_bill_id", kwargs={"bill_id": 1})

        response = self.client.put(url)

        json = response.json()
        expected = {
            "detail": "You (user: 1) don't have this capability: crud_provisioning_bill for academy 1",
            "status_code": 403,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # When: no bill
    # Then: should return 404
    def test_no_bill(self):

        model = self.bc.database.create(user=1, profile_academy=1, role=1, capability="crud_provisioning_bill")
        self.client.force_authenticate(model.user)

        self.headers(academy=1)

        url = reverse_lazy("provisioning:academy_bill_id", kwargs={"bill_id": 1})

        response = self.client.put(url)

        content = response.json()
        expected = {
            "detail": "not-found",
            "status_code": 404,
        }

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.bc.database.list_of("provisioning.ProvisioningBill"), [])

    # When: bill
    # Then: should return 404
    def test_bill(self):

        model = self.bc.database.create(
            user=1, profile_academy=1, role=1, capability="crud_provisioning_bill", provisioning_bill=1
        )
        self.client.force_authenticate(model.user)

        self.headers(academy=1)

        url = reverse_lazy("provisioning:academy_bill_id", kwargs={"bill_id": 1})

        response = self.client.put(url)

        content = response.json()
        expected = put_serializer(model.provisioning_bill)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningBill"),
            [
                self.bc.format.to_dict(model.provisioning_bill),
            ],
        )

    # When: bill
    # Then: should return 404
    def test_bill__valid_statuses(self):
        statuses = ["DUE", "DISPUTED", "IGNORED", "PENDING"]

        model = self.bc.database.create(
            user=1, profile_academy=1, role=1, capability="crud_provisioning_bill", provisioning_bill=1
        )
        self.client.force_authenticate(model.user)

        self.headers(academy=1)

        url = reverse_lazy("provisioning:academy_bill_id", kwargs={"bill_id": 1})

        for s in statuses:
            data = {"status": s}
            response = self.client.put(url, data, format="json")

            content = response.json()
            expected = put_serializer(model.provisioning_bill, data=data)

            self.assertEqual(content, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(
                self.bc.database.list_of("provisioning.ProvisioningBill"),
                [
                    {
                        **self.bc.format.to_dict(model.provisioning_bill),
                        **data,
                    }
                ],
            )

    # When: change the status, the status is valid
    # Then: should return 200
    def test_bill__valid_statuses__but_status_is_paid_or_error(self):
        statuses = ["DUE", "DISPUTED", "IGNORED", "PENDING"]

        provisioning_bill = {"status": random.choice(["PAID", "ERROR"])}

        model = self.bc.database.create(
            user=1, profile_academy=1, role=1, capability="crud_provisioning_bill", provisioning_bill=provisioning_bill
        )
        self.client.force_authenticate(model.user)

        self.headers(academy=1)

        url = reverse_lazy("provisioning:academy_bill_id", kwargs={"bill_id": 1})

        for s in statuses:
            data = {"status": s}
            response = self.client.put(url, data, format="json")

            content = response.json()
            expected = {"detail": "readonly-bill-status", "status_code": 400}

            self.assertEqual(content, expected)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(
                self.bc.database.list_of("provisioning.ProvisioningBill"),
                [
                    self.bc.format.to_dict(model.provisioning_bill),
                ],
            )

    # When: change the status, but the status is invalid
    # Then: should return 200
    def test_bill__invalid_statuses(self):
        statuses = ["PAID", "ERROR"]

        model = self.bc.database.create(
            user=1, profile_academy=1, role=1, capability="crud_provisioning_bill", provisioning_bill=1
        )
        self.client.force_authenticate(model.user)

        self.headers(academy=1)

        url = reverse_lazy("provisioning:academy_bill_id", kwargs={"bill_id": 1})

        for s in statuses:
            data = {"status": s}
            response = self.client.put(url, data, format="json")

            content = response.json()
            expected = {"detail": "invalid-bill-status", "status_code": 400}

            self.assertEqual(content, expected)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(
                self.bc.database.list_of("provisioning.ProvisioningBill"),
                [
                    self.bc.format.to_dict(model.provisioning_bill),
                ],
            )
