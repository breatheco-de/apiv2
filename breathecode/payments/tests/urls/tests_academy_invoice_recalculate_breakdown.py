"""
Tests for POST /v1/payments/academy/invoice/<id>/recalculate-breakdown
"""
from unittest.mock import MagicMock, patch

from django.urls import reverse_lazy
from django.utils import timezone
from rest_framework import status

from ..mixins import PaymentsTestCase

UTC_NOW = timezone.now()


class AcademyInvoiceRecalculateBreakdownTestSuite(PaymentsTestCase):
    def test_no_auth(self):
        url = reverse_lazy("payments:academy_invoice_id_recalculate_breakdown", kwargs={"invoice_id": 1})
        response = self.client.post(url)
        json = response.json()
        expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_no_capability(self):
        model = self.bc.database.create(user=1)
        self.client.force_authenticate(model.user)
        self.bc.request.set_headers(academy=1)
        url = reverse_lazy("payments:academy_invoice_id_recalculate_breakdown", kwargs={"invoice_id": 1})
        response = self.client.post(url)
        json = response.json()
        expected = {
            "detail": "You (user: 1) don't have this capability: issue_refund for academy 1",
            "status_code": 403,
        }
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_invoice_not_found(self):
        model = self.bc.database.create(
            user=1,
            capability="issue_refund",
            role=1,
            profile_academy=1,
            skip_cohort=True,
        )
        self.client.force_authenticate(model.user)
        self.bc.request.set_headers(academy=1)
        url = reverse_lazy("payments:academy_invoice_id_recalculate_breakdown", kwargs={"invoice_id": 999})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch("breathecode.payments.views.actions.calculate_invoice_breakdown")
    def test_success(self, mock_calculate):
        breakdown = {"plans": {"full-stack": {"amount": 100.0, "currency": "USD"}}, "service-items": {}}
        mock_calculate.return_value = breakdown

        model = self.bc.database.create(
            user=1,
            academy=1,
            capability="issue_refund",
            role=1,
            profile_academy=1,
            skip_cohort=True,
            currency=1,
            bag={"chosen_period": "MONTH", "how_many_installments": 0},
            invoice={"paid_at": UTC_NOW, "status": "FULFILLED", "academy_id": 1, "user_id": 1, "amount": 100.0},
        )
        self.client.force_authenticate(model.user)
        self.bc.request.set_headers(academy=1)
        url = reverse_lazy(
            "payments:academy_invoice_id_recalculate_breakdown",
            kwargs={"invoice_id": model.invoice.id},
        )
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        json = response.json()
        self.assertEqual(json["amount_breakdown"], breakdown)
        mock_calculate.assert_called_once()

        invoice = self.bc.database.get("payments.Invoice", model.invoice.id, dict=False)
        self.assertEqual(invoice.amount_breakdown, breakdown)
