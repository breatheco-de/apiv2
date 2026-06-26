"""
Tests for /v1/payments/academy/planoffer endpoints
"""

from unittest.mock import patch

from django.urls import reverse_lazy
from django.utils import timezone
from rest_framework import status

from breathecode.payments.caches import PlanOfferCache

from ..mixins import PaymentsTestCase

UTC_NOW = timezone.now()


class AcademyPlanOfferTestSuite(PaymentsTestCase):
    def _create_owned_plans(self, capability="crud_subscription"):
        model = self.bc.database.create(
            user=1,
            role=1,
            capability=capability,
            profile_academy=1,
            academy=1,
            currency=1,
            plan=2,
            service=1,
            service_item=2,
        )
        model.plan[0].owner = model.academy
        model.plan[0].save()
        model.plan[1].owner = model.academy
        model.plan[1].save()
        return model

    def test_get__no_auth(self):
        url = reverse_lazy("payments:academy_planoffer")
        response = self.client.get(url, headers={"academy": 1})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get__no_capability(self):
        model = self.bc.database.create(user=1, role=1, academy=1, profile_academy=1)
        self.client.force_authenticate(model.user)
        url = reverse_lazy("payments:academy_planoffer")
        response = self.client.get(url, headers={"academy": 1})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get__empty(self):
        model = self.bc.database.create(user=1, role=1, capability="read_subscription", profile_academy=1)
        self.client.force_authenticate(model.user)
        url = reverse_lazy("payments:academy_planoffer")
        response = self.client.get(url, headers={"academy": 1})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), [])

    def test_get__lists_academy_owned_original_plan_offers_only(self):
        model = self._create_owned_plans(capability="read_subscription")
        other_academy = self.bc.database.create(academy=1).academy

        foreign_plan = model.plan[0]
        foreign_plan.owner = other_academy
        foreign_plan.save()

        plan_offer = {
            "original_plan_id": model.plan[0].id,
            "suggested_plan_id": model.plan[1].id,
            "show_modal": True,
            "expires_at": None,
        }
        self.bc.database.create(plan_offer=plan_offer, plan_offer_translation=1)

        self.client.force_authenticate(model.user)
        url = reverse_lazy("payments:academy_planoffer")
        response = self.client.get(url, headers={"academy": 1})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), [])

    def test_get__filter_by_like_on_original_plan(self):
        model = self._create_owned_plans(capability="read_subscription")
        model.plan[0].slug = "premium-bootcamp-2025"
        model.plan[0].title = "Premium Bootcamp"
        model.plan[0].save()
        model.plan[1].slug = "basic-plan"
        model.plan[1].title = "Basic Plan"
        model.plan[1].save()

        plan_offers = [
            {
                "original_plan_id": model.plan[0].id,
                "suggested_plan_id": model.plan[1].id,
                "show_modal": True,
                "expires_at": None,
            },
            {
                "original_plan_id": model.plan[1].id,
                "suggested_plan_id": model.plan[0].id,
                "show_modal": False,
                "expires_at": None,
            },
        ]
        self.bc.database.create(plan_offer=plan_offers, plan_offer_translation=1)

        self.client.force_authenticate(model.user)
        url = reverse_lazy("payments:academy_planoffer") + "?like=bootcamp"
        response = self.client.get(url, headers={"academy": 1})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        json = response.json()
        self.assertEqual(len(json), 1)
        self.assertEqual(json[0]["original_plan"]["slug"], "premium-bootcamp-2025")

    def test_get__by_id(self):
        model = self._create_owned_plans(capability="read_subscription")
        plan_offer = {
            "original_plan_id": model.plan[0].id,
            "suggested_plan_id": model.plan[1].id,
            "show_modal": True,
            "expires_at": None,
        }
        offer_model = self.bc.database.create(
            plan_offer=plan_offer,
            plan_offer_translation={
                "lang": "en",
                "title": "Upgrade",
                "description": "Get premium",
                "short_description": "Premium",
            },
        )

        self.client.force_authenticate(model.user)
        url = reverse_lazy("payments:academy_planoffer_id", kwargs={"plan_offer_id": offer_model.plan_offer.id})
        response = self.client.get(url, headers={"academy": 1})
        json = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json["id"], offer_model.plan_offer.id)
        self.assertEqual(json["show_modal"], True)
        self.assertEqual(len(json["translations"]), 1)
        self.assertEqual(json["translations"][0]["lang"], "en")
        self.assertEqual(json["original_plan"]["id"], model.plan[0].id)
        self.assertEqual(json["suggested_plan"]["id"], model.plan[1].id)

    def test_post__no_capability(self):
        model = self._create_owned_plans(capability="read_subscription")
        self.client.force_authenticate(model.user)
        url = reverse_lazy("payments:academy_planoffer")
        data = {
            "original_plan": model.plan[0].slug,
            "suggested_plan": model.plan[1].slug,
            "translations": [
                {
                    "lang": "en",
                    "title": "Upgrade",
                    "description": "Get premium",
                    "short_description": "Premium",
                }
            ],
        }
        response = self.client.post(url, data, format="json", headers={"academy": 1})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch("breathecode.payments.views.PlanOfferCache.clear")
    def test_post__success(self, mock_clear):
        model = self._create_owned_plans()
        self.client.force_authenticate(model.user)
        url = reverse_lazy("payments:academy_planoffer")
        data = {
            "original_plan": model.plan[0].slug,
            "suggested_plan": model.plan[1].slug,
            "show_modal": True,
            "translations": [
                {
                    "lang": "en",
                    "title": "Upgrade",
                    "description": "Get premium",
                    "short_description": "Premium",
                },
                {
                    "lang": "es",
                    "title": "Mejora",
                    "description": "Obtén premium",
                    "short_description": "Premium",
                },
            ],
        }
        response = self.client.post(url, data, format="json", headers={"academy": 1})
        json = response.json()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(json["show_modal"], True)
        self.assertEqual(len(json["translations"]), 2)
        mock_clear.assert_called_once()
        self.assertEqual(self.bc.database.list_of("payments.PlanOffer"), 1)
        self.assertEqual(self.bc.database.list_of("payments.PlanOfferTranslation"), 2)

    def test_post__foreign_original_plan(self):
        model = self._create_owned_plans()
        other_academy = self.bc.database.create(academy=1).academy
        foreign_plan = model.plan[0]
        foreign_plan.owner = other_academy
        foreign_plan.save()

        self.client.force_authenticate(model.user)
        url = reverse_lazy("payments:academy_planoffer")
        data = {
            "original_plan": foreign_plan.slug,
            "suggested_plan": model.plan[1].slug,
            "translations": [
                {
                    "lang": "en",
                    "title": "Upgrade",
                    "description": "Get premium",
                    "short_description": "Premium",
                }
            ],
        }
        response = self.client.post(url, data, format="json", headers={"academy": 1})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_post__duplicate_active_offer(self):
        model = self._create_owned_plans()
        plan_offer = {
            "original_plan_id": model.plan[0].id,
            "suggested_plan_id": model.plan[1].id,
            "show_modal": True,
            "expires_at": None,
        }
        self.bc.database.create(plan_offer=plan_offer)

        self.client.force_authenticate(model.user)
        url = reverse_lazy("payments:academy_planoffer")
        data = {
            "original_plan": model.plan[0].slug,
            "suggested_plan": model.plan[1].slug,
            "translations": [
                {
                    "lang": "en",
                    "title": "Upgrade",
                    "description": "Get premium",
                    "short_description": "Premium",
                }
            ],
        }
        response = self.client.post(url, data, format="json", headers={"academy": 1})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["slug"], "active-plan-offer-exists")

    @patch("breathecode.payments.views.PlanOfferCache.clear")
    def test_put__updates_offer_and_upserts_translation(self, mock_clear):
        model = self._create_owned_plans()
        plan_offer = {
            "original_plan_id": model.plan[0].id,
            "suggested_plan_id": model.plan[1].id,
            "show_modal": False,
            "expires_at": None,
        }
        offer_model = self.bc.database.create(
            plan_offer=plan_offer,
            plan_offer_translation={
                "lang": "en",
                "title": "Old title",
                "description": "Old description",
                "short_description": "Old short",
            },
        )

        self.client.force_authenticate(model.user)
        url = reverse_lazy("payments:academy_planoffer_id", kwargs={"plan_offer_id": offer_model.plan_offer.id})
        data = {
            "show_modal": True,
            "translations": [
                {
                    "lang": "en",
                    "title": "New title",
                    "description": "New description",
                    "short_description": "New short",
                },
                {
                    "lang": "es",
                    "title": "Nuevo",
                    "description": "Nueva descripcion",
                    "short_description": "Nuevo corto",
                },
            ],
        }
        response = self.client.put(url, data, format="json", headers={"academy": 1})
        json = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json["show_modal"], True)
        self.assertEqual(len(json["translations"]), 2)
        mock_clear.assert_called_once()

        offer_model.plan_offer.refresh_from_db()
        self.assertEqual(offer_model.plan_offer.show_modal, True)

    @patch("breathecode.payments.views.PlanOfferCache.clear")
    def test_delete__removes_offer(self, mock_clear):
        model = self._create_owned_plans()
        plan_offer = {
            "original_plan_id": model.plan[0].id,
            "suggested_plan_id": model.plan[1].id,
            "show_modal": True,
            "expires_at": None,
        }
        offer_model = self.bc.database.create(plan_offer=plan_offer, plan_offer_translation=1)

        self.client.force_authenticate(model.user)
        url = reverse_lazy("payments:academy_planoffer_id", kwargs={"plan_offer_id": offer_model.plan_offer.id})
        response = self.client.delete(url, headers={"academy": 1})

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        mock_clear.assert_called_once()
        self.assertEqual(self.bc.database.list_of("payments.PlanOffer"), [])
        self.assertEqual(self.bc.database.list_of("payments.PlanOfferTranslation"), [])
