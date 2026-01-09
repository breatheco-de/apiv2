from datetime import timedelta
from unittest.mock import MagicMock, call, patch

from django.urls import reverse_lazy
from django.utils import timezone
from rest_framework import status

from breathecode.payments.models import Invoice
from breathecode.payments.tests.mixins import PaymentsTestCase

UTC_NOW = timezone.now()


class CoinbaseWebhookViewTestSuite(PaymentsTestCase):

    def test__post__missing_signature(self):
        url = reverse_lazy("payments:coinbase_callback")
        data = {"event": {"type": "charge:pending", "data": {}}}
        response = self.client.post(url, data, format="json")

        json = response.json()
        expected = {"detail": "missing-signature", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test__post__charge_created__returns_ok(self):
        model = self.bc.database.create(bag=1, currency=1)

        url = reverse_lazy("payments:coinbase_callback")
        data = {
            "event": {
                "type": "charge:created",
                "data": {
                    "id": "CHARGE123",
                    "metadata": {"bag_id": model.bag.id, "amount": "100.0"},
                },
            }
        }
        headers = {"HTTP_X_CC_WEBHOOK_SIGNATURE": "valid_signature"}

        with patch("breathecode.payments.services.coinbase.CoinbaseCommerce.verify_webhook_signature") as mock_verify:
            mock_verify.return_value = True
            response = self.client.post(url, data, format="json", **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test__post__missing_bag_id(self):
        url = reverse_lazy("payments:coinbase_callback")
        data = {
            "event": {
                "type": "charge:pending",
                "data": {
                    "id": "CHARGE123",
                    "metadata": {"amount": "100.0"},
                },
            }
        }
        headers = {"HTTP_X_CC_WEBHOOK_SIGNATURE": "valid_signature"}

        response = self.client.post(url, data, format="json", **headers)

        json = response.json()
        expected = {"detail": "missing-bag-id", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test__post__bag_not_found(self):
        url = reverse_lazy("payments:coinbase_callback")
        data = {
            "event": {
                "type": "charge:pending",
                "data": {
                    "id": "CHARGE123",
                    "metadata": {"bag_id": 999, "amount": "100.0"},
                },
            }
        }
        headers = {"HTTP_X_CC_WEBHOOK_SIGNATURE": "valid_signature"}

        response = self.client.post(url, data, format="json", **headers)

        json = response.json()
        expected = {"detail": "bag-not-found", "status_code": 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test__post__missing_amount(self):
        model = self.bc.database.create(bag=1, currency=1)

        url = reverse_lazy("payments:coinbase_callback")
        data = {
            "event": {
                "type": "charge:pending",
                "data": {
                    "id": "CHARGE123",
                    "metadata": {"bag_id": model.bag.id},
                },
            }
        }
        headers = {"HTTP_X_CC_WEBHOOK_SIGNATURE": "valid_signature"}

        response = self.client.post(url, data, format="json", **headers)

        json = response.json()
        expected = {"detail": "missing-amount", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("breathecode.payments.tasks.charge_subscription.delay")
    def test__post__charge_confirmed__already_fulfilled(self, mock_charge_task):
        invoice = {
            "status": "FULFILLED",
            "coinbase_charge_id": "CHARGE123",
            "amount": 100.0,
        }
        bag = {"status": "PAID", "was_delivered": True}
        model = self.bc.database.create(invoice=invoice, bag=bag, currency=1, user=1, academy=1)

        url = reverse_lazy("payments:coinbase_callback")
        data = {
            "event": {
                "type": "charge:confirmed",
                "data": {
                    "id": "CHARGE123",
                    "metadata": {
                        "bag_id": model.bag.id,
                        "amount": "100.0",
                    },
                },
            }
        }
        headers = {"HTTP_X_CC_WEBHOOK_SIGNATURE": "valid_signature"}

        with patch("breathecode.payments.services.coinbase.CoinbaseCommerce.verify_webhook_signature") as mock_verify:
            mock_verify.return_value = True
            response = self.client.post(url, data, format="json", **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify invoice status remains unchanged
        model.invoice.refresh_from_db()
        self.assertEqual(model.invoice.status, "FULFILLED")
