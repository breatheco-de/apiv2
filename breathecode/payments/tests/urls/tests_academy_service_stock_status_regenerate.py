"""
Tests for POST /v1/payments/academy/service/stock_status/regenerate endpoint.
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
        url = reverse_lazy("payments:academy_service_stock_status_regenerate")
        response = self.client.post(url, headers={"academy": 1}, data={"subscription_id": 1}, format="json")
        json = response.json()

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertTrue("Authentication credentials were not provided" in json.get("detail", ""))

    """
    🔽🔽🔽 Success payload
    """

    @pytest.mark.django_db
    def test_with_capability_and_success_payload(self):
        model = self.bc.database.create(country=1, city=1, user=1, role=1, capability="crud_consumable", profile_academy=1)
        self.bc.request.authenticate(model.user)

        expected = {
            "target": {
                "type": "subscription",
                "id": 1,
                "academy_id": 1,
                "user_id": 1,
                "seat_id": None,
            },
            "status": "success",
            "error_stage": None,
            "execution_error": None,
            "message": "Service stock regeneration executed successfully",
        }

        regenerate_mock = MagicMock(return_value=expected)
        with patch.object(actions, "regenerate_service_stock_for_target", regenerate_mock):
            url = reverse_lazy("payments:academy_service_stock_status_regenerate")
            response = self.client.post(url, headers={"academy": 1}, data={"subscription_id": 1}, format="json")
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
                        "plan_financing_id": None,
                        "subscription_id": 1,
                        "seat_id": None,
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
            "target": {
                "type": "subscription",
                "id": 1,
                "academy_id": 1,
                "user_id": 1,
                "seat_id": None,
            },
            "status": "failed",
            "error_stage": "build_service_stock_scheduler",
            "execution_error": "cannot build schedulers",
            "message": "Failed while building service stock schedulers: cannot build schedulers",
        }
        with patch.object(actions, "regenerate_service_stock_for_target", MagicMock(return_value=expected)):
            url = reverse_lazy("payments:academy_service_stock_status_regenerate")
            response = self.client.post(url, headers={"academy": 1}, data={"subscription_id": 1}, format="json")
            json = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json, expected)
