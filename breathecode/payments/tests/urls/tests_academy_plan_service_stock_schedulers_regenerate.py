"""
Tests for POST /v1/payments/academy/plan/<plan_id>/service/stock/schedulers/regenerate
"""

from unittest.mock import MagicMock, call, patch

import pytest
from django.urls import reverse_lazy
from rest_framework import status

from breathecode.payments import actions, tasks

from ..mixins import PaymentsTestCase


@pytest.fixture(autouse=True)
def setup(db):
    yield


class AcademyPlanServiceStockSchedulersRegenerateSuite(PaymentsTestCase):
    def test_without_auth(self):
        url = reverse_lazy("payments:academy_plan_service_stock_schedulers_regenerate", kwargs={"plan_id": 1})
        response = self.client.post(url, headers={"academy": 1})
        json = response.json()

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertTrue("Authentication credentials were not provided" in json.get("detail", ""))

    @pytest.mark.django_db
    def test_forbidden_without_manage_service_stock_schedulers(self):
        plan = {"slug": "p2", "owner": None}
        model = self.bc.database.create(
            country=1,
            city=1,
            user=1,
            academy=1,
            plan=plan,
            role=1,
            capability="crud_consumable",
            profile_academy=1,
        )
        self.bc.request.authenticate(model.user)

        url = reverse_lazy(
            "payments:academy_plan_service_stock_schedulers_regenerate",
            kwargs={"plan_id": model.plan.id},
        )
        response = self.client.post(url, headers={"academy": 1})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @pytest.mark.django_db
    def test_plan_not_found(self):
        model = self.bc.database.create(country=1, city=1, user=1, role=1, capability="manage_service_stock_schedulers", profile_academy=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy("payments:academy_plan_service_stock_schedulers_regenerate", kwargs={"plan_id": 99999})
        response = self.client.post(url, headers={"academy": 1})

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @pytest.mark.django_db
    def test_post_by_slug(self):
        model = self.bc.database.create(
            country=1,
            city=1,
            user=1,
            academy=1,
            plan={"slug": "test-plan-slug-regen", "owner": None},
            role=1,
            capability="manage_service_stock_schedulers",
            profile_academy=1,
        )
        self.bc.request.authenticate(model.user)

        expected = MagicMock(return_value={"plan_id": model.plan.id})
        with patch.object(actions, "enqueue_service_stock_regeneration_for_plan", expected):
            url = reverse_lazy(
                "payments:academy_plan_slug_service_stock_schedulers_regenerate",
                kwargs={"plan_slug": "test-plan-slug-regen"},
            )
            response = self.client.post(url, headers={"academy": 1})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected.assert_called_once_with(academy_id=1, plan_id=model.plan.id)

    @pytest.mark.django_db
    def test_queues_matching_targets(self):
        plan = {"slug": "p1", "owner": None}
        plan_financing = {"status": "ACTIVE"}
        subscription = {"status": "ACTIVE"}

        model = self.bc.database.create(
            country=1,
            city=1,
            user=1,
            academy=1,
            plan=plan,
            plan_financing=plan_financing,
            subscription=subscription,
            role=1,
            capability="manage_service_stock_schedulers",
            profile_academy=1,
        )
        self.bc.request.authenticate(model.user)

        model.plan_financing.plans.add(model.plan)
        model.subscription.plans.add(model.plan)

        with patch.object(tasks.build_service_stock_scheduler_from_plan_financing, "delay", MagicMock()) as pf_delay:
            with patch.object(tasks.build_service_stock_scheduler_from_subscription, "delay", MagicMock()) as sub_delay:
                url = reverse_lazy(
                    "payments:academy_plan_service_stock_schedulers_regenerate",
                    kwargs={"plan_id": model.plan.id},
                )
                response = self.client.post(url, headers={"academy": 1})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.json()
        self.assertEqual(body["total_queued"], 2)
        self.assertEqual(body["plan_financing_ids_queued"], [model.plan_financing.id])
        self.assertEqual(body["subscription_ids_queued"], [model.subscription.id])

        self.assertEqual(pf_delay.call_args_list, [call(model.plan_financing.id)])
        self.assertEqual(sub_delay.call_args_list, [call(model.subscription.id)])
