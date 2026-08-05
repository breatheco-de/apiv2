"""
Tests for /v1/payments/academy/coupon endpoints
"""

from datetime import timedelta

from django.urls import reverse_lazy
from django.utils import timezone
from rest_framework import status

from ..mixins import PaymentsTestCase


class AcademyCouponTestSuite(PaymentsTestCase):
    def _auth(self, capability="read_subscription"):
        model = self.bc.database.create(
            user=1,
            role=1,
            capability=capability,
            profile_academy=1,
            academy=1,
        )
        self.client.force_authenticate(model.user)
        return model

    def test_get__no_auth(self):
        url = reverse_lazy("payments:academy_coupon")
        response = self.client.get(url, headers={"academy": 1})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get__no_capability(self):
        model = self.bc.database.create(user=1, role=1, academy=1, profile_academy=1)
        self.client.force_authenticate(model.user)
        url = reverse_lazy("payments:academy_coupon")
        response = self.client.get(url, headers={"academy": 1})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get__returns_currently_offered_by_default(self):
        model = self._auth()
        now = timezone.now()
        self.bc.database.create(
            coupon=[
                {
                    "slug": "active-coupon",
                    "discount_value": 0.2,
                    "offered_at": now - timedelta(days=1),
                    "expires_at": now + timedelta(days=30),
                    "how_many_offers": 5,
                },
                {
                    "slug": "expired-coupon",
                    "discount_value": 0.2,
                    "offered_at": now - timedelta(days=30),
                    "expires_at": now - timedelta(days=1),
                    "how_many_offers": 5,
                },
                {
                    "slug": "disabled-coupon",
                    "discount_value": 0.2,
                    "offered_at": now - timedelta(days=1),
                    "expires_at": now + timedelta(days=30),
                    "how_many_offers": 0,
                },
                {
                    "slug": "not-yet-offered",
                    "discount_value": 0.2,
                    "offered_at": now + timedelta(days=1),
                    "expires_at": now + timedelta(days=30),
                    "how_many_offers": 5,
                },
            ]
        )

        url = reverse_lazy("payments:academy_coupon")
        response = self.client.get(url, headers={"academy": model.academy.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.json()
        self.assertEqual({item["slug"] for item in payload}, {"active-coupon"})
        self.assertIn("plans", payload[0])
        self.assertIn("how_many_offers", payload[0])

    def test_get__status_all_includes_inactive(self):
        model = self._auth()
        now = timezone.now()
        self.bc.database.create(
            coupon=[
                {
                    "slug": "active-coupon",
                    "discount_value": 0.2,
                    "offered_at": now - timedelta(days=1),
                    "expires_at": now + timedelta(days=30),
                    "how_many_offers": 5,
                },
                {
                    "slug": "expired-coupon",
                    "discount_value": 0.2,
                    "offered_at": now - timedelta(days=30),
                    "expires_at": now - timedelta(days=1),
                    "how_many_offers": 5,
                },
            ]
        )

        url = reverse_lazy("payments:academy_coupon") + "?status=all"
        response = self.client.get(url, headers={"academy": model.academy.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual({item["slug"] for item in response.json()}, {"active-coupon", "expired-coupon"})

    def test_get__includes_coupons_without_plans(self):
        model = self._auth()
        now = timezone.now()
        created = self.bc.database.create(
            coupon={
                "slug": "no-plans-global",
                "discount_value": 0.2,
                "offered_at": now - timedelta(days=1),
                "expires_at": now + timedelta(days=30),
                "how_many_offers": -1,
            }
        )

        url = reverse_lazy("payments:academy_coupon")
        response = self.client.get(url, headers={"academy": model.academy.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.json()
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["slug"], created.coupon.slug)
        self.assertEqual(payload[0]["plans"], [])

    def test_get__filter_by_plan_slug(self):
        model = self._auth()
        now = timezone.now()
        created = self.bc.database.create(
            coupon=[
                {
                    "slug": "plan-coupon",
                    "discount_value": 0.1,
                    "offered_at": now - timedelta(days=1),
                    "expires_at": now + timedelta(days=30),
                    "how_many_offers": -1,
                },
                {
                    "slug": "other-coupon",
                    "discount_value": 0.2,
                    "offered_at": now - timedelta(days=1),
                    "expires_at": now + timedelta(days=30),
                    "how_many_offers": -1,
                },
            ],
            plan={"slug": "full-stack"},
            currency=1,
        )
        created.plan.owner = model.academy
        created.plan.save()
        created.coupon[0].plans.add(created.plan)

        url = reverse_lazy("payments:academy_coupon") + "?plan=full-stack"
        response = self.client.get(url, headers={"academy": model.academy.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.json()
        self.assertEqual({item["slug"] for item in payload}, {"plan-coupon"})
        self.assertEqual(payload[0]["plans"][0]["slug"], "full-stack")

    def test_get__excludes_referral_coupons_by_default(self):
        model = self._auth()
        now = timezone.now()
        self.bc.database.create(
            coupon=[
                {
                    "slug": "promo-coupon",
                    "discount_value": 0.2,
                    "referral_type": "NO_REFERRAL",
                    "referral_value": 0,
                    "offered_at": now - timedelta(days=1),
                    "expires_at": now + timedelta(days=30),
                    "how_many_offers": -1,
                },
                {
                    "slug": "referral-percentage",
                    "discount_value": 0.1,
                    "referral_type": "PERCENTAGE",
                    "referral_value": 0.1,
                    "offered_at": now - timedelta(days=1),
                    "expires_at": now + timedelta(days=30),
                    "how_many_offers": -1,
                },
            ]
        )

        url = reverse_lazy("payments:academy_coupon")
        response = self.client.get(url, headers={"academy": model.academy.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual({item["slug"] for item in response.json()}, {"promo-coupon"})

    def test_get__include_referral_true(self):
        model = self._auth()
        now = timezone.now()
        self.bc.database.create(
            coupon=[
                {
                    "slug": "promo-coupon",
                    "discount_value": 0.2,
                    "referral_type": "NO_REFERRAL",
                    "referral_value": 0,
                    "offered_at": now - timedelta(days=1),
                    "expires_at": now + timedelta(days=30),
                    "how_many_offers": -1,
                },
                {
                    "slug": "referral-percentage",
                    "discount_value": 0.1,
                    "referral_type": "PERCENTAGE",
                    "referral_value": 0.1,
                    "offered_at": now - timedelta(days=1),
                    "expires_at": now + timedelta(days=30),
                    "how_many_offers": -1,
                },
            ]
        )

        url = reverse_lazy("payments:academy_coupon") + "?include_referral=true"
        response = self.client.get(url, headers={"academy": model.academy.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual({item["slug"] for item in response.json()}, {"promo-coupon", "referral-percentage"})

    def test_post__creates_coupon_for_specific_plan(self):
        model = self._auth(capability="crud_subscription")
        created = self.bc.database.create(plan={"slug": "full-stack"}, currency=1)
        created.plan.owner = model.academy
        created.plan.save()

        url = reverse_lazy("payments:academy_coupon")
        response = self.client.post(
            url,
            data={
                "slug": "summer-plan",
                "discount_type": "PERCENT_OFF",
                "discount_value": 0.25,
                "referral_type": "NO_REFERRAL",
                "referral_value": 0,
                "plans": ["full-stack"],
                "how_many_offers": 10,
            },
            format="json",
            headers={"academy": model.academy.id},
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        payload = response.json()
        self.assertEqual(payload["slug"], "summer-plan")
        self.assertEqual(payload["how_many_offers"], 10)
        self.assertEqual(len(payload["plans"]), 1)
        self.assertEqual(payload["plans"][0]["slug"], "full-stack")

    def test_put__updates_coupon_without_plans(self):
        model = self._auth(capability="crud_subscription")
        now = timezone.now()
        created = self.bc.database.create(
            coupon={
                "slug": "no-plans-global",
                "discount_value": 0.2,
                "offered_at": now - timedelta(days=1),
                "expires_at": now + timedelta(days=30),
                "how_many_offers": -1,
            }
        )

        url = reverse_lazy("payments:academy_coupon_slug", kwargs={"coupon_slug": created.coupon.slug})
        response = self.client.put(
            url,
            data={"discount_value": 0.35},
            format="json",
            headers={"academy": model.academy.id},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["discount_value"], 0.35)
        self.assertEqual(response.json()["plans"], [])
        created.coupon.refresh_from_db()
        self.assertEqual(created.coupon.discount_value, 0.35)

    def test_delete__removes_coupon_without_plans(self):
        model = self._auth(capability="crud_subscription")
        now = timezone.now()
        created = self.bc.database.create(
            coupon={
                "slug": "no-plans-global",
                "discount_value": 0.2,
                "offered_at": now - timedelta(days=1),
                "expires_at": now + timedelta(days=30),
                "how_many_offers": -1,
            }
        )

        url = reverse_lazy("payments:academy_coupon_slug", kwargs={"coupon_slug": created.coupon.slug})
        response = self.client.delete(url, headers={"academy": model.academy.id})

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.bc.database.list_of("payments.Coupon"), [])
