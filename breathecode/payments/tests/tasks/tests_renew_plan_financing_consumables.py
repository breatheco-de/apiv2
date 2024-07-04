"""
Test /answer
"""

import logging
import random
from unittest.mock import MagicMock, call, patch

from dateutil.relativedelta import relativedelta
from django.utils import timezone

from breathecode.payments import tasks
from breathecode.payments.actions import calculate_relative_delta

from ...tasks import renew_plan_financing_consumables
from ..mixins import PaymentsTestCase

UTC_NOW = timezone.now()


def service_stock_scheduler_item(data={}):
    return {
        "id": 1,
        "plan_handler_id": None,
        "subscription_handler_id": None,
        "valid_until": None,
        **data,
    }


# FIXME: create fail in this test file
class PaymentsTestSuite(PaymentsTestCase):
    """
    🔽🔽🔽 Subscription not found
    """

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_subscription_not_found(self):
        renew_plan_financing_consumables.delay(1)

        self.assertEqual(self.bc.database.list_of("admissions.Cohort"), [])

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting renew_plan_financing_consumables for id 1"),
                # retrying
                call("Starting renew_plan_financing_consumables for id 1"),
            ],
        )
        self.assertEqual(
            logging.Logger.error.call_args_list,
            [
                call("PlanFinancing with id 1 not found", exc_info=True),
            ],
        )

        self.assertEqual(self.bc.database.list_of("payments.PlanFinancing"), [])

    """
    🔽🔽🔽 Subscription was not paid
    """

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.payments.tasks.renew_consumables.delay", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_subscription_was_not_paid(self):
        subscription = {
            "next_payment_at": UTC_NOW - relativedelta(seconds=1),
            "valid_until": UTC_NOW + relativedelta(minutes=3),
            "plan_expires_at": UTC_NOW + relativedelta(minutes=3),
            "monthly_price": random.random() * 99.99 + 0.01,
        }
        plan = {"is_renewable": False}
        model = self.bc.database.create(plan_financing=subscription, plan=plan)

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        renew_plan_financing_consumables.delay(1)

        self.assertEqual(self.bc.database.list_of("admissions.Cohort"), [])

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting renew_plan_financing_consumables for id 1"),
            ],
        )
        self.assertEqual(
            logging.Logger.error.call_args_list,
            [
                call("The PlanFinancing 1 needs to be paid to renew the consumables", exc_info=True),
            ],
        )

        self.assertEqual(tasks.renew_consumables.delay.call_args_list, [])

        self.assertEqual(
            self.bc.database.list_of("payments.PlanFinancing"),
            [
                self.bc.format.to_dict(model.plan_financing),
            ],
        )
        self.assertEqual(self.bc.database.list_of("payments.ServiceStockScheduler"), [])

    """
    🔽🔽🔽 Subscription was paid
    """

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.payments.tasks.renew_consumables.delay", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_subscription_was_paid__without_stock_scheduler(self):
        subscription = {
            "valid_until": UTC_NOW + relativedelta(minutes=3),
            "next_payment_at": UTC_NOW + relativedelta(minutes=3),
            "plan_expires_at": UTC_NOW + relativedelta(minutes=3),
            "monthly_price": random.random() * 99.99 + 0.01,
        }
        plan = {"is_renewable": False}
        model = self.bc.database.create(plan_financing=subscription, plan=plan)

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        renew_plan_financing_consumables.delay(1)

        self.assertEqual(self.bc.database.list_of("admissions.Cohort"), [])

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting renew_plan_financing_consumables for id 1"),
            ],
        )
        self.assertEqual(logging.Logger.error.call_args_list, [])

        self.assertEqual(tasks.renew_consumables.delay.call_args_list, [])

        self.assertEqual(
            self.bc.database.list_of("payments.PlanFinancing"),
            [
                self.bc.format.to_dict(model.plan_financing),
            ],
        )
        self.assertEqual(self.bc.database.list_of("payments.ServiceStockScheduler"), [])

    """
    🔽🔽🔽 Subscription was not paid
    """

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.payments.tasks.renew_consumables.delay", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_subscription_was_not_paid__(self):
        plan_service_items = [
            {
                "plan_id": 1,
                "service_item_id": n,
            }
            for n in range(1, 3)
        ] + [
            {
                "plan_id": 2,
                "service_item_id": n,
            }
            for n in range(3, 5)
        ]
        plan_service_item_handlers = [{"handler_id": n} for n in range(1, 5)]
        subscription = {
            "next_payment_at": UTC_NOW + relativedelta(minutes=3),
            "valid_until": UTC_NOW + relativedelta(minutes=3),
            "plan_expires_at": UTC_NOW + relativedelta(minutes=3),
            "monthly_price": random.random() * 99.99 + 0.01,
        }

        service_stock_schedulers = [
            {
                "subscription_handler_id": None,
                "plan_handler_id": n,
            }
            for n in range(1, 5)
        ]

        plan = {"is_renewable": False}

        model = self.bc.database.create(
            plan_financing=subscription,
            service_stock_scheduler=service_stock_schedulers,
            plan=(2, plan),
            service_item=4,
            plan_service_item=plan_service_items,
            plan_service_item_handler=plan_service_item_handlers,
        )

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        renew_plan_financing_consumables.delay(1)

        self.assertEqual(self.bc.database.list_of("admissions.Cohort"), [])

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting renew_plan_financing_consumables for id 1"),
            ],
        )
        self.assertEqual(logging.Logger.error.call_args_list, [])

        self.assertEqual(
            tasks.renew_consumables.delay.call_args_list,
            [
                call(1),
                call(2),
                call(3),
                call(4),
            ],
        )

        self.assertEqual(
            self.bc.database.list_of("payments.PlanFinancing"),
            [
                self.bc.format.to_dict(model.plan_financing),
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("payments.ServiceStockScheduler"),
            self.bc.format.to_dict(model.service_stock_scheduler),
        )
