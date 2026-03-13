"""
Tests for GET /v1/payments/academy/invoice (list) with date_start and date_end.
"""
from datetime import timedelta

from django.urls import reverse_lazy
from django.utils import timezone
from rest_framework import status

from ..mixins import PaymentsTestCase

UTC_NOW = timezone.now()


class AcademyInvoiceListTestSuite(PaymentsTestCase):
    def test_no_auth(self):
        url = reverse_lazy("payments:academy_invoice")
        response = self.client.get(url)
        json = response.json()
        expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_no_capability(self):
        model = self.bc.database.create(user=1)
        self.client.force_authenticate(model.user)
        self.bc.request.set_headers(academy=1)
        url = reverse_lazy("payments:academy_invoice")
        response = self.client.get(url)
        json = response.json()
        expected = {
            "detail": "You (user: 1) don't have this capability: read_invoice for academy 1",
            "status_code": 403,
        }
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_invalid_date_start_returns_400(self):
        model = self.bc.database.create(
            user=1,
            capability="read_invoice",
            role=1,
            profile_academy=1,
            skip_cohort=True,
        )
        self.client.force_authenticate(model.user)
        self.bc.request.set_headers(academy=1)
        url = reverse_lazy("payments:academy_invoice") + "?date_start=not-a-datetime"
        response = self.client.get(url)
        json = response.json()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        detail = json.get("detail")
        slug = detail.get("slug") if isinstance(detail, dict) else detail
        self.assertEqual(slug, "invalid-datetime")

    def test_invalid_date_end_returns_400(self):
        model = self.bc.database.create(
            user=1,
            capability="read_invoice",
            role=1,
            profile_academy=1,
            skip_cohort=True,
        )
        self.client.force_authenticate(model.user)
        self.bc.request.set_headers(academy=1)
        url = reverse_lazy("payments:academy_invoice") + "?date_end=invalid"
        response = self.client.get(url)
        json = response.json()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        detail = json.get("detail")
        slug = detail.get("slug") if isinstance(detail, dict) else detail
        self.assertEqual(slug, "invalid-datetime")

    def test_date_start_and_date_end_filter_by_paid_at(self):
        """Invoices outside the range are excluded."""
        start = UTC_NOW - timedelta(days=10)
        end = UTC_NOW - timedelta(days=2)
        # Invoice inside range
        paid_inside = start + timedelta(days=2)
        # Invoice before range
        paid_before = start - timedelta(days=2)
        # Invoice after range
        paid_after = end + timedelta(days=2)

        model = self.bc.database.create(
            user=1,
            academy=1,
            capability="read_invoice",
            role=1,
            profile_academy=1,
            skip_cohort=True,
            currency=1,
            bag=3,
            invoice=[
                {"paid_at": paid_before, "status": "FULFILLED", "academy_id": 1, "user_id": 1},
                {"paid_at": paid_inside, "status": "FULFILLED", "academy_id": 1, "user_id": 1},
                {"paid_at": paid_after, "status": "FULFILLED", "academy_id": 1, "user_id": 1},
            ],
        )
        self.client.force_authenticate(model.user)
        self.bc.request.set_headers(academy=1)

        date_start_str = start.strftime("%Y-%m-%dT%H:%M:%SZ")
        date_end_str = end.strftime("%Y-%m-%dT%H:%M:%SZ")
        url = reverse_lazy("payments:academy_invoice") + f"?date_start={date_start_str}&date_end={date_end_str}"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        # Only the invoice with paid_at in [start, end] should be returned
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], model.invoice[1].id)
