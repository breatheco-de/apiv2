"""
Tests for regenerate_service_stock_for_target action.
"""

from unittest.mock import MagicMock, patch

import pytest
from dateutil.relativedelta import relativedelta
from django.utils import timezone

from breathecode.payments import actions, tasks
from breathecode.payments.models import Consumable, PlanFinancingTeam, ServiceStockScheduler

from ..mixins import PaymentsTestCase


@pytest.fixture(autouse=True)
def setup(db):
    yield


class PaymentsTestSuite(PaymentsTestCase):
    """
    🔽🔽🔽 Successful regeneration
    """

    @pytest.mark.django_db
    def test_regenerate_service_stock_for_target__plan_financing_success(self):
        plan_financing = {
            "next_payment_at": timezone.now() + relativedelta(months=1),
            "plan_expires_at": timezone.now() + relativedelta(months=2),
            "monthly_price": 100,
        }
        model = self.bc.database.create(
            country=1,
            city=1,
            academy=1,
            user=1,
            plan_financing=plan_financing,
            plan={"is_renewable": False},
            service={"type": "VOID"},
            service_item={"service_id": 1, "how_many": 1},
            plan_service_item={"plan_id": 1, "service_item_id": 1},
        )

        with (
            patch.object(
                tasks.renew_plan_financing_consumables,
                "delay",
                MagicMock(
                    side_effect=lambda plan_financing_id, seat_id=None: tasks.renew_plan_financing_consumables.apply(
                        args=[plan_financing_id],
                        kwargs={"seat_id": seat_id},
                        throw=True,
                    )
                )
            ),
            patch.object(
                tasks.renew_consumables,
                "delay",
                MagicMock(side_effect=lambda scheduler_id: tasks.renew_consumables.apply(args=[scheduler_id], throw=True)),
            ),
        ):
            response = actions.regenerate_service_stock_for_target(
                academy_id=model.academy.id,
                plan_financing_id=model.plan_financing.id,
            )

        self.assertEqual(response["status"], "success")
        self.assertEqual(response["execution_error"], None)
        self.assertEqual(response["error_stage"], None)
        self.assertTrue(ServiceStockScheduler.objects.filter(plan_handler__plan_financing_id=model.plan_financing.id).exists())
        self.assertTrue(Consumable.objects.filter(plan_financing_id=model.plan_financing.id).exists())

    """
    🔽🔽🔽 Successful regeneration (subscription)
    """

    @pytest.mark.django_db
    def test_regenerate_service_stock_for_target__subscription_success(self):
        subscription = {
            "next_payment_at": timezone.now() + relativedelta(months=1),
            "valid_until": timezone.now() + relativedelta(months=2),
            "seat_service_item_id": None,
        }
        model = self.bc.database.create(
            country=1,
            city=1,
            academy=1,
            user=1,
            subscription=subscription,
            service={"type": "VOID"},
            service_item={"service_id": 1, "how_many": 1},
            subscription_service_item={"subscription_id": 1, "service_item_id": 1},
        )

        with (
            patch.object(
                tasks.renew_subscription_consumables,
                "delay",
                MagicMock(
                    side_effect=lambda subscription_id, seat_id=None: tasks.renew_subscription_consumables.apply(
                        args=[subscription_id],
                        kwargs={"seat_id": seat_id},
                        throw=True,
                    )
                ),
            ),
            patch.object(
                tasks.renew_consumables,
                "delay",
                MagicMock(side_effect=lambda scheduler_id: tasks.renew_consumables.apply(args=[scheduler_id], throw=True)),
            ),
        ):
            response = actions.regenerate_service_stock_for_target(
                academy_id=model.academy.id,
                subscription_id=model.subscription.id,
            )

        self.assertEqual(response["status"], "success")
        self.assertEqual(response["execution_error"], None)
        self.assertEqual(response["error_stage"], None)
        self.assertEqual(response["target"]["type"], "subscription")
        self.assertTrue(ServiceStockScheduler.objects.filter(subscription_handler__subscription_id=model.subscription.id).exists())
        self.assertTrue(Consumable.objects.filter(subscription_id=model.subscription.id).exists())

    """
    🔽🔽🔽 Failure while building service stock schedulers (plan financing)
    """

    @pytest.mark.django_db
    def test_regenerate_service_stock_for_target__plan_financing_build_error(self):
        plan_financing = {
            "monthly_price": 100,
            "next_payment_at": timezone.now() + relativedelta(months=1),
            "plan_expires_at": timezone.now() + relativedelta(months=2),
        }
        model = self.bc.database.create(country=1, city=1, academy=1, user=1, plan_financing=plan_financing)
        PlanFinancingTeam.objects.create(financing=model.plan_financing, name="test-team")

        response = actions.regenerate_service_stock_for_target(
            academy_id=model.academy.id,
            plan_financing_id=model.plan_financing.id,
            seat_id=999999,
        )

        self.assertEqual(response["status"], "failed")
        self.assertEqual(response["target"]["type"], "plan_financing")
        self.assertEqual(response["target"]["id"], model.plan_financing.id)
        self.assertEqual(response["error_stage"], "build_service_stock_scheduler")
        self.assertTrue("PlanFinancingSeat with id 999999 not found" in response["execution_error"])
        self.assertTrue("Failed while building service stock schedulers:" in response["message"])

    """
    🔽🔽🔽 Failure while building service stock schedulers (subscription)
    """

    @pytest.mark.django_db
    def test_regenerate_service_stock_for_target__subscription_build_error(self):
        subscription = {
            "next_payment_at": timezone.now() + relativedelta(months=1),
            "valid_until": timezone.now() + relativedelta(months=2),
            "seat_service_item_id": None,
        }
        model = self.bc.database.create(country=1, city=1, academy=1, user=1, subscription=subscription)

        response = actions.regenerate_service_stock_for_target(
            academy_id=model.academy.id,
            subscription_id=model.subscription.id,
            seat_id=999999,
        )

        self.assertEqual(response["status"], "failed")
        self.assertEqual(response["target"]["type"], "subscription")
        self.assertEqual(response["target"]["id"], model.subscription.id)
        self.assertEqual(response["error_stage"], "build_service_stock_scheduler")
        self.assertTrue("SubscriptionSeat with id 999999 not found" in response["execution_error"])
        self.assertTrue("Failed while building service stock schedulers:" in response["message"])

    @pytest.mark.django_db
    def test_regenerate_service_stock_for_target__fails_if_no_scheduler_was_created(self):
        plan_financing = {
            "next_payment_at": timezone.now() + relativedelta(months=1),
            "plan_expires_at": timezone.now() + relativedelta(months=2),
            "monthly_price": 100,
        }
        model = self.bc.database.create(
            country=1,
            city=1,
            academy=1,
            user=1,
            plan_financing=plan_financing,
        )

        with patch.object(actions, "_run_service_stock_build_task_sync", MagicMock()):
            response = actions.regenerate_service_stock_for_target(
                academy_id=model.academy.id,
                plan_financing_id=model.plan_financing.id,
            )

        self.assertEqual(response["status"], "failed")
        self.assertEqual(response["error_stage"], "post_condition")
        self.assertEqual(response["execution_error"], "No service stock scheduler was created during regeneration")