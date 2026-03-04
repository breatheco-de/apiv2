"""
Tests for regenerate_consumable_for_service_stock_scheduler action.
"""

from unittest.mock import MagicMock, patch

import pytest
from capyc.rest_framework.exceptions import ValidationException
from dateutil.relativedelta import relativedelta
from django.utils import timezone

from breathecode.payments import actions

from ..mixins import PaymentsTestCase


@pytest.fixture(autouse=True)
def setup(db):
    yield


class PaymentsTestSuite(PaymentsTestCase):
    """
    🔽🔽🔽 Successful consumable regeneration by scheduler
    """

    @pytest.mark.django_db
    def test_regenerate_consumable_for_service_stock_scheduler__success(self):
        plan_financing = {
            "monthly_price": 100,
            "next_payment_at": timezone.now() + relativedelta(months=1),
            "plan_expires_at": timezone.now() + relativedelta(months=2),
        }
        model = self.bc.database.create(
            service_stock_scheduler=1,
            plan={"is_renewable": False},
            academy={"available_as_saas": True},
            country=1,
            city=1,
            service_item={"how_many": -1},
            service={"type": "SEAT"},
            plan_financing=plan_financing,
            plan_service_item_handler=1,
        )

        with patch.object(actions, "_run_renew_consumable_task_sync", MagicMock()) as renew_mock:
            response = actions.regenerate_consumable_for_service_stock_scheduler(
                academy_id=model.academy.id,
                service_stock_scheduler_id=model.service_stock_scheduler.id,
            )

        self.assertEqual(response["status"], "success")
        self.assertEqual(response["error_stage"], None)
        self.assertEqual(response["execution_error"], None)
        self.assertEqual(response["scheduler"]["id"], model.service_stock_scheduler.id)
        self.assertEqual(response["scheduler"]["academy_id"], model.academy.id)
        self.assertEqual(renew_mock.call_args_list, [((model.service_stock_scheduler.id,), {})])

    """
    🔽🔽🔽 Scheduler not found in academy
    """

    @pytest.mark.django_db
    def test_regenerate_consumable_for_service_stock_scheduler__scheduler_not_found(self):
        with self.assertRaises(ValidationException):
            actions.regenerate_consumable_for_service_stock_scheduler(
                academy_id=1,
                service_stock_scheduler_id=999999,
            )

    """
    🔽🔽🔽 Failure while renewing consumable (AbortTask real message)
    """

    @pytest.mark.django_db
    def test_regenerate_consumable_for_service_stock_scheduler__renew_abort_task_message(self):
        plan_financing = {
            "monthly_price": 100,
            "next_payment_at": timezone.now() + relativedelta(months=1),
            "plan_expires_at": timezone.now() - relativedelta(minutes=1),
        }
        model = self.bc.database.create(
            service_stock_scheduler=1,
            plan={"is_renewable": False},
            academy={"available_as_saas": True},
            country=1,
            city=1,
            service_item={"how_many": -1},
            service={"type": "SEAT"},
            plan_financing=plan_financing,
            plan_service_item_handler=1,
        )

        response = actions.regenerate_consumable_for_service_stock_scheduler(
            academy_id=model.academy.id,
            service_stock_scheduler_id=model.service_stock_scheduler.id,
        )

        self.assertEqual(response["status"], "failed")
        self.assertEqual(response["error_stage"], "renew_consumable")
        self.assertEqual(response["execution_error"], f"The plan financing {model.plan_financing.id} is over")
        self.assertEqual(
            response["message"],
            f"Failed while renewing consumables for service stock scheduler: The plan financing {model.plan_financing.id} is over",
        )
