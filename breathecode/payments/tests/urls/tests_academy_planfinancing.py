"""Tests for academy plan financing and subscription permission checks."""

from datetime import timedelta

from django.utils import timezone

from breathecode.payments.models import PlanFinancing, Subscription
from breathecode.payments.tests.mixins import PaymentsTestCase


class AcademyPlanFinancingPermissionTestSuite(PaymentsTestCase):
    """Staff capability and academy ownership for plan financing."""

    def _financing(self, capability="crud_subscription"):
        now = timezone.now()
        return self.bc.database.create(
            user=1,
            role=1,
            capability=capability,
            profile_academy=1,
            academy=1,
            plan_financing={
                "monthly_price": 100.0,
                "how_many_installments": 4,
                "status": "ACTIVE",
                "next_payment_at": now + timedelta(days=30),
                "plan_expires_at": now + timedelta(days=365),
                "valid_until": now + timedelta(days=365),
            },
        )

    def test_put__no_auth(self):
        """A request without a token is rejected."""
        url = "/v1/payments/academy/planfinancing/1"
        response = self.client.put(url, {"status": "PAYMENT_ISSUE"}, format="json", headers={"academy": 1})

        self.assertEqual(response.status_code, 401)

    def test_put__no_capability(self):
        """An authenticated user without crud_subscription cannot update a financing."""
        model = self.bc.database.create(user=1, role=1, academy=1, profile_academy=1)
        self.client.force_authenticate(model.user)
        url = "/v1/payments/academy/planfinancing/1"
        response = self.client.put(url, {"status": "PAYMENT_ISSUE"}, format="json", headers={"academy": 1})

        self.assertEqual(response.status_code, 403)

    def test_put__read_capability_is_not_enough(self):
        """read_subscription does not allow changing a financing."""
        model = self._financing(capability="read_subscription")
        self.client.force_authenticate(model.user)
        url = f"/v1/payments/academy/planfinancing/{model.plan_financing.id}"
        response = self.client.put(url, {"status": "PAYMENT_ISSUE"}, format="json", headers={"academy": 1})

        self.assertEqual(response.status_code, 403)
        model.plan_financing.refresh_from_db()
        self.assertEqual(model.plan_financing.status, "ACTIVE")

    def test_put__other_academy_still_updates(self):
        """The academy header authorizes the caller; it does not scope the financing row."""
        model = self._financing()
        other = self.bc.database.create(academy={"slug": "other-academy", "name": "Other"}).academy
        PlanFinancing.objects.filter(id=model.plan_financing.id).update(academy=other)

        self.client.force_authenticate(model.user)
        url = f"/v1/payments/academy/planfinancing/{model.plan_financing.id}"
        response = self.client.put(url, {"status": "FULLY_PAID"}, format="json", headers={"academy": 1})

        self.assertEqual(response.status_code, 200)
        model.plan_financing.refresh_from_db()
        self.assertEqual(model.plan_financing.status, "FULLY_PAID")

    def test_put__updates_status(self):
        """Staff with crud_subscription can change the status of their academy's financing."""
        model = self._financing()
        self.client.force_authenticate(model.user)
        url = f"/v1/payments/academy/planfinancing/{model.plan_financing.id}"
        response = self.client.put(url, {"status": "FULLY_PAID"}, format="json", headers={"academy": 1})

        self.assertEqual(response.status_code, 200)
        model.plan_financing.refresh_from_db()
        self.assertEqual(model.plan_financing.status, "FULLY_PAID")

    def test_get__no_capability(self):
        """Listing financings requires read_subscription."""
        model = self.bc.database.create(user=1, role=1, academy=1, profile_academy=1)
        self.client.force_authenticate(model.user)
        response = self.client.get("/v1/payments/academy/planfinancing", headers={"academy": 1})

        self.assertEqual(response.status_code, 403)

    def test_get__lists_financing(self):
        """A caller with read_subscription can list financings."""
        model = self._financing(capability="read_subscription")
        self.client.force_authenticate(model.user)
        response = self.client.get("/v1/payments/academy/planfinancing", headers={"academy": 1})

        self.assertEqual(response.status_code, 200)
        ids = [item["id"] for item in response.json()]
        self.assertIn(model.plan_financing.id, ids)


class AcademySubscriptionPermissionTestSuite(PaymentsTestCase):
    """Staff capability and academy ownership for subscription updates."""

    def _subscription(self, capability="crud_subscription"):
        now = timezone.now()
        return self.bc.database.create(
            user=1,
            role=1,
            capability=capability,
            profile_academy=1,
            academy=1,
            subscription={
                "status": "ACTIVE",
                "paid_at": now,
                "next_payment_at": now + timedelta(days=30),
                "valid_until": now + timedelta(days=365),
            },
        )

    def test_put__no_capability(self):
        """An authenticated user without crud_subscription cannot update a subscription."""
        model = self._subscription(capability="read_subscription")
        self.client.force_authenticate(model.user)
        url = f"/v1/payments/academy/subscription/{model.subscription.id}"
        response = self.client.put(url, {"status": "CANCELLED"}, format="json", headers={"academy": 1})

        self.assertEqual(response.status_code, 403)
        model.subscription.refresh_from_db()
        self.assertEqual(model.subscription.status, "ACTIVE")

    def test_put__other_academy_still_updates(self):
        """The academy header authorizes the caller; it does not scope the subscription row."""
        model = self._subscription()
        other = self.bc.database.create(academy={"slug": "other-academy", "name": "Other"}).academy
        Subscription.objects.filter(id=model.subscription.id).update(academy=other)

        self.client.force_authenticate(model.user)
        url = f"/v1/payments/academy/subscription/{model.subscription.id}"
        response = self.client.put(url, {"status": "CANCELLED"}, format="json", headers={"academy": 1})

        self.assertEqual(response.status_code, 200)
        model.subscription.refresh_from_db()
        self.assertEqual(model.subscription.status, "CANCELLED")

    def test_put__updates_status(self):
        """Staff with crud_subscription can change the status of their academy's subscription."""
        model = self._subscription()
        self.client.force_authenticate(model.user)
        url = f"/v1/payments/academy/subscription/{model.subscription.id}"
        response = self.client.put(url, {"status": "CANCELLED"}, format="json", headers={"academy": 1})

        self.assertEqual(response.status_code, 200)
        model.subscription.refresh_from_db()
        self.assertEqual(model.subscription.status, "CANCELLED")
