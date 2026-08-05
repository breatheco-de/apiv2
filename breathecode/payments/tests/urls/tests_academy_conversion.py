"""
Tests for GET /v1/payments/academy/conversion
"""

from datetime import timedelta

from django.urls import reverse_lazy
from django.utils import timezone
from rest_framework import status

from ..mixins import PaymentsTestCase

UTC_NOW = timezone.now()


class AcademyConversionTestSuite(PaymentsTestCase):
    def test_no_auth(self):
        url = reverse_lazy("payments:academy_conversion")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(
            response.json(),
            {"detail": "Authentication credentials were not provided.", "status_code": 401},
        )

    def test_no_capability(self):
        model = self.bc.database.create(user=1)
        self.client.force_authenticate(model.user)
        self.bc.request.set_headers(academy=1)

        url = reverse_lazy("payments:academy_conversion")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            response.json(),
            {
                "detail": "You (user: 1) don't have this capability: read_subscription for academy 1",
                "status_code": 403,
            },
        )

    def test_filters_by_utm_referrer_and_includes_invoices(self):
        model = self.bc.database.create(
            user=1,
            capability="read_subscription",
            role=1,
            profile_academy=1,
            academy=1,
            currency=1,
            plan=1,
            skip_cohort=True,
        )
        buyer = self.bc.database.create(user=1).user

        matching_subscription = self.bc.database.create(
            user=buyer,
            academy=model.academy,
            currency=model.currency,
            subscription={
                "conversion_info": {"utm_referrer": "marcia@4geeksacademy.com", "utm_source": "admissions"},
            },
            skip_cohort=True,
        ).subscription
        matching_subscription.plans.add(model.plan)

        invoice = self.bc.database.create(
            user=buyer,
            academy=model.academy,
            currency=model.currency,
            invoice={"amount": 150.0, "status": "FULFILLED", "paid_at": UTC_NOW},
            skip_cohort=True,
        ).invoice
        matching_subscription.invoices.add(invoice)

        self.bc.database.create(
            user=buyer,
            academy=model.academy,
            currency=model.currency,
            subscription={
                "conversion_info": {"utm_referrer": "someoneelse@4geeksacademy.com"},
            },
            skip_cohort=True,
        )

        matching_financing = self.bc.database.create(
            user=buyer,
            academy=model.academy,
            currency=model.currency,
            plan_financing={
                "conversion_info": {"utm_referrer": "marcia@4geeksacademy.com"},
                "monthly_price": 99.0,
                "how_many_installments": 3,
                "next_payment_at": UTC_NOW + timedelta(days=30),
                "valid_until": UTC_NOW + timedelta(days=90),
                "plan_expires_at": UTC_NOW + timedelta(days=365),
            },
            skip_cohort=True,
        ).plan_financing
        matching_financing.plans.add(model.plan)

        financing_invoice = self.bc.database.create(
            user=buyer,
            academy=model.academy,
            currency=model.currency,
            invoice={"amount": 99.0, "status": "FULFILLED", "paid_at": UTC_NOW},
            skip_cohort=True,
        ).invoice
        matching_financing.invoices.add(financing_invoice)

        self.client.force_authenticate(model.user)
        self.bc.request.set_headers(academy=1)

        url = reverse_lazy("payments:academy_conversion") + "?utm_referrer=marcia@4geeksacademy.com"
        response = self.client.get(url)
        data = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(data["subscriptions"]), 1)
        self.assertEqual(len(data["plan_financings"]), 1)

        subscription = data["subscriptions"][0]
        self.assertEqual(subscription["id"], matching_subscription.id)
        self.assertEqual(subscription["conversion_info"]["utm_referrer"], "marcia@4geeksacademy.com")
        self.assertEqual(len(subscription["invoices"]), 1)
        self.assertEqual(subscription["invoices"][0]["id"], invoice.id)
        self.assertEqual(subscription["invoices"][0]["amount"], 150.0)
        self.assertEqual(subscription["invoices"][0]["status"], "FULFILLED")

        financing = data["plan_financings"][0]
        self.assertEqual(financing["id"], matching_financing.id)
        self.assertEqual(financing["conversion_info"]["utm_referrer"], "marcia@4geeksacademy.com")
        self.assertEqual(len(financing["invoices"]), 1)
        self.assertEqual(financing["invoices"][0]["id"], financing_invoice.id)
        self.assertEqual(financing["invoices"][0]["amount"], 99.0)

    def test_sale_filter_returns_400(self):
        model = self.bc.database.create(
            user=1,
            capability="read_subscription",
            role=1,
            profile_academy=1,
            skip_cohort=True,
        )
        self.client.force_authenticate(model.user)
        self.bc.request.set_headers(academy=1)

        url = reverse_lazy("payments:academy_conversion") + "?sale=anything"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        detail = response.json().get("detail")
        slug = detail.get("slug") if isinstance(detail, dict) else detail
        self.assertEqual(slug, "conversion-info-sale-filter-unsupported")

    def test_scopes_to_academy(self):
        model = self.bc.database.create(
            user=1,
            capability="read_subscription",
            role=1,
            profile_academy=1,
            academy=1,
            currency=1,
            skip_cohort=True,
        )
        other_academy = self.bc.database.create(academy=1).academy

        own = self.bc.database.create(
            user=model.user,
            academy=model.academy,
            currency=model.currency,
            subscription={"conversion_info": {"utm_referrer": "max@4geeksacademy.com"}},
            skip_cohort=True,
        ).subscription

        self.bc.database.create(
            user=model.user,
            academy=other_academy,
            currency=model.currency,
            subscription={"conversion_info": {"utm_referrer": "max@4geeksacademy.com"}},
            skip_cohort=True,
        )

        self.client.force_authenticate(model.user)
        self.bc.request.set_headers(academy=1)

        url = reverse_lazy("payments:academy_conversion") + "?utm_referrer=max@4geeksacademy.com"
        response = self.client.get(url)
        data = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item["id"] for item in data["subscriptions"]], [own.id])
        self.assertEqual(data["plan_financings"], [])

    def test_has_requires_all_listed_conversion_info_keys(self):
        model = self.bc.database.create(
            user=1,
            capability="read_subscription",
            role=1,
            profile_academy=1,
            academy=1,
            currency=1,
            skip_cohort=True,
        )
        buyer = self.bc.database.create(user=1).user

        with_both = self.bc.database.create(
            user=buyer,
            academy=model.academy,
            currency=model.currency,
            subscription={
                "conversion_info": {
                    "utm_referrer": "marcia@4geeksacademy.com",
                    "utm_source": "admissions",
                },
            },
            skip_cohort=True,
        ).subscription

        self.bc.database.create(
            user=buyer,
            academy=model.academy,
            currency=model.currency,
            subscription={
                "conversion_info": {"utm_referrer": "marcia@4geeksacademy.com"},
            },
            skip_cohort=True,
        )

        self.bc.database.create(
            user=buyer,
            academy=model.academy,
            currency=model.currency,
            subscription={"conversion_info": {"landing_url": "/checkout"}},
            skip_cohort=True,
        )

        self.client.force_authenticate(model.user)
        self.bc.request.set_headers(academy=1)

        url = reverse_lazy("payments:academy_conversion") + "?has=utm_referrer,utm_source"
        response = self.client.get(url)
        data = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item["id"] for item in data["subscriptions"]], [with_both.id])
        self.assertEqual(data["plan_financings"], [])

    def test_has_with_invalid_key_returns_400(self):
        model = self.bc.database.create(
            user=1,
            capability="read_subscription",
            role=1,
            profile_academy=1,
            skip_cohort=True,
        )
        self.client.force_authenticate(model.user)
        self.bc.request.set_headers(academy=1)

        url = reverse_lazy("payments:academy_conversion") + "?has=utm_referrer,not_a_real_key"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        detail = response.json().get("detail")
        slug = detail.get("slug") if isinstance(detail, dict) else detail
        self.assertEqual(slug, "conversion-info-has-invalid-key")
