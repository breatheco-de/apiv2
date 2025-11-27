from unittest.mock import MagicMock, patch

from django.urls import reverse_lazy
from rest_framework import status

from breathecode.payments.tests.mixins import PaymentsTestCase


class CoinbaseChargeViewTestSuite(PaymentsTestCase):

    def test__get__no_auth(self):
        url = reverse_lazy("payments:coinbase_charge_info", kwargs={"charge_id": "CHARGE123"})
        response = self.client.get(url)

        json = response.json()
        expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch("breathecode.payments.services.coinbase.CoinbaseCommerce.get_charge")
    def test__get__without_academy(self, mock_get_charge):
        mock_get_charge.return_value = {
            "id": "CHARGE123",
            "code": "TESTCODE",
            "pricing": {"local": {"amount": "100.00", "currency": "USD"}},
            "timeline": [{"status": "NEW", "time": "2024-01-01T00:00:00Z"}],
        }

        model = self.bc.database.create(user=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:coinbase_charge_info", kwargs={"charge_id": "CHARGE123"})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        json = response.json()
        self.assertEqual(json["id"], "CHARGE123")
        self.assertEqual(json["code"], "TESTCODE")

    def test__get__academy_not_found(self):
        model = self.bc.database.create(user=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:coinbase_charge_info", kwargs={"charge_id": "CHARGE123"}) + "?academy=999"
        response = self.client.get(url)

        json = response.json()
        expected = {"detail": "academy-not-found", "status_code": 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch("breathecode.payments.services.coinbase.CoinbaseCommerce.get_charge")
    def test__get__with_academy(self, mock_get_charge):
        mock_get_charge.return_value = {
            "id": "CHARGE123",
            "code": "TESTCODE",
            "pricing": {"local": {"amount": "100.00", "currency": "USD"}},
            "timeline": [{"status": "NEW", "time": "2024-01-01T00:00:00Z"}],
        }

        model = self.bc.database.create(user=1, academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:coinbase_charge_info", kwargs={"charge_id": "CHARGE123"}) + "?academy=1"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        json = response.json()
        self.assertEqual(json["id"], "CHARGE123")
        self.assertEqual(json["code"], "TESTCODE")

    @patch("breathecode.payments.services.coinbase.CoinbaseCommerce.get_charge")
    def test__get__error_retrieving_charge(self, mock_get_charge):
        mock_get_charge.side_effect = Exception("Coinbase API error")

        model = self.bc.database.create(user=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("payments:coinbase_charge_info", kwargs={"charge_id": "CHARGE123"})
        response = self.client.get(url)

        json = response.json()
        expected = {"detail": "charge-retrieval-error", "status_code": 500}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
