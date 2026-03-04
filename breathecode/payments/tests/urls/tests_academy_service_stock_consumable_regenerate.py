"""
Tests for POST /v1/payments/academy/service/stock_status/consumable/regenerate endpoint.
"""

from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse_lazy
from rest_framework import status

from breathecode.payments import actions

from ..mixins import PaymentsTestCase


@pytest.fixture(autouse=True)
def setup(db):
    yield


class PaymentsTestSuite(PaymentsTestCase):
    """
    🔽🔽🔽 Without authentication
    """

    def test_without_auth(self):
        url = reverse_lazy("payments:academy_service_stock_consumable_regenerate")
        response = self.client.post(url, headers={"academy": 1}, data={"service_stock_scheduler_id": 1}, format="json")
        json = response.json()

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertTrue("Authentication credentials were not provided" in json.get("detail", ""))

    """
    🔽🔽🔽 Missing scheduler id
    """

    @pytest.mark.django_db
    def test_missing_service_stock_scheduler_id(self):
        model = self.bc.database.create(country=1, city=1, user=1, role=1, capability="crud_consumable", profile_academy=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy("payments:academy_service_stock_consumable_regenerate")
        response = self.client.post(url, headers={"academy": 1}, data={}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    """
    🔽🔽🔽 Success payload
    """

    @pytest.mark.django_db
    def test_with_capability_and_success_payload(self):
        model = self.bc.database.create(country=1, city=1, user=1, role=1, capability="crud_consumable", profile_academy=1)
        self.bc.request.authenticate(model.user)

        expected = {
            "scheduler": {"id": 1, "academy_id": 1},
            "status": "success",
            "error_stage": None,
            "execution_error": None,
            "message": "Consumable regeneration executed successfully",
        }

        regenerate_mock = MagicMock(return_value=expected)
        with patch.object(actions, "regenerate_consumable_for_service_stock_scheduler", regenerate_mock):
            url = reverse_lazy("payments:academy_service_stock_consumable_regenerate")
            response = self.client.post(
                url,
                headers={"academy": 1},
                data={"service_stock_scheduler_id": "1"},
                format="json",
            )
            json = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json, expected)
        self.assertEqual(
            regenerate_mock.call_args_list,
            [
                (
                    (),
                    {
                        "academy_id": 1,
                        "service_stock_scheduler_id": 1,
                    },
                )
            ],
        )

    """
    🔽🔽🔽 Failed payload with clear stage and message
    """

    @pytest.mark.django_db
    def test_with_capability_and_failed_payload(self):
        model = self.bc.database.create(country=1, city=1, user=1, role=1, capability="crud_consumable", profile_academy=1)
        self.bc.request.authenticate(model.user)

        expected = {
            "scheduler": {"id": 1, "academy_id": 1},
            "status": "failed",
            "error_stage": "renew_consumable",
            "execution_error": "The plan financing 1 is over",
            "message": "Failed while renewing consumables for service stock scheduler: The plan financing 1 is over",
        }

        with patch.object(actions, "regenerate_consumable_for_service_stock_scheduler", MagicMock(return_value=expected)):
            url = reverse_lazy("payments:academy_service_stock_consumable_regenerate")
            response = self.client.post(
                url,
                headers={"academy": 1},
                data={"service_stock_scheduler_id": 1},
                format="json",
            )
            json = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json, expected)
