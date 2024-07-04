"""
Test /answer
"""

import logging
import random
from unittest.mock import MagicMock, call, patch

from django.utils import timezone
from breathecode.payments import tasks
from breathecode.payments.actions import calculate_relative_delta

from ...tasks import build_service_stock_scheduler_from_plan_financing

from ..mixins import PaymentsTestCase
from dateutil.relativedelta import relativedelta

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
    def test_subscription_not_found(self):
        build_service_stock_scheduler_from_plan_financing.delay(1)

        self.assertEqual(self.bc.database.list_of("admissions.Cohort"), [])

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting build_service_stock_scheduler_from_plan_financing for subscription 1"),
                # retrying
                call("Starting build_service_stock_scheduler_from_plan_financing for subscription 1"),
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
    🔽🔽🔽 With Subscription
    """

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.payments.tasks.renew_plan_financing_consumables.delay", MagicMock())
    def test_subscription_exists(self):
        subscription = {
            "plan_expires_at": UTC_NOW + relativedelta(months=2),
            "monthly_price": (random.random() * 99.99) + 0.01,
        }
        model = self.bc.database.create(plan_financing=subscription)

        # remove prints from mixer
        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        build_service_stock_scheduler_from_plan_financing.delay(1)

        self.assertEqual(self.bc.database.list_of("admissions.Cohort"), [])

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [call("Starting build_service_stock_scheduler_from_plan_financing for subscription 1")],
        )
        self.assertEqual(logging.Logger.error.call_args_list, [])

        self.assertEqual(
            self.bc.database.list_of("payments.PlanFinancing"),
            [
                self.bc.format.to_dict(model.plan_financing),
            ],
        )
        self.assertEqual(tasks.renew_plan_financing_consumables.delay.call_args_list, [call(1)])
        self.bc.check.queryset_with_pks(model.plan_financing.plans.all(), [])

        self.assertEqual(self.bc.database.list_of("payments.ServiceStockScheduler"), [])

    """
    🔽🔽🔽 With Subscription with one ServiceItem
    """

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.payments.tasks.renew_plan_financing_consumables.delay", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_subscription_with_service_item(self):
        subscription = {
            "next_payment_at": UTC_NOW + relativedelta(months=1),
            "plan_expires_at": UTC_NOW + relativedelta(months=2),
            "valid_until": UTC_NOW + relativedelta(months=3),
            "monthly_price": (random.random() * 99.99) + 0.01,
        }
        plan = {"is_renewable": False}
        model = self.bc.database.create(plan_financing=subscription, service_item=1, plan_service_item=1, plan=plan)

        # remove prints from mixer
        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        build_service_stock_scheduler_from_plan_financing.delay(1)

        self.assertEqual(self.bc.database.list_of("admissions.Cohort"), [])

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting build_service_stock_scheduler_from_plan_financing for subscription 1"),
            ],
        )
        self.assertEqual(logging.Logger.error.call_args_list, [])

        self.assertEqual(
            self.bc.database.list_of("payments.PlanFinancing"),
            [
                self.bc.format.to_dict(model.plan_financing),
            ],
        )
        self.assertEqual(tasks.renew_plan_financing_consumables.delay.call_args_list, [call(1)])
        self.bc.check.queryset_with_pks(model.plan_financing.plans.all(), [1])

        self.assertEqual(
            self.bc.database.list_of("payments.ServiceStockScheduler"),
            [
                service_stock_scheduler_item(
                    {
                        "valid_until": None,
                        "plan_handler_id": 1,
                    }
                ),
            ],
        )

    """
    🔽🔽🔽 With Subscription with one Plan with ServiceItem
    """

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.payments.tasks.renew_plan_financing_consumables.delay", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_subscription_with_plan(self):
        subscription = {
            "next_payment_at": UTC_NOW + relativedelta(months=1),
            "plan_expires_at": UTC_NOW + relativedelta(months=2),
            "valid_until": UTC_NOW + relativedelta(months=3),
            "monthly_price": (random.random() * 99.99) + 0.01,
        }

        plan = {"is_renewable": False}

        model = self.bc.database.create(plan_financing=subscription, plan=plan, plan_service_item=1)

        # remove prints from mixer
        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        build_service_stock_scheduler_from_plan_financing.delay(1)

        self.assertEqual(self.bc.database.list_of("admissions.Cohort"), [])

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting build_service_stock_scheduler_from_plan_financing for subscription 1"),
            ],
        )
        self.assertEqual(logging.Logger.error.call_args_list, [])

        self.assertEqual(
            self.bc.database.list_of("payments.PlanFinancing"),
            [
                self.bc.format.to_dict(model.plan_financing),
            ],
        )
        self.assertEqual(tasks.renew_plan_financing_consumables.delay.call_args_list, [call(1)])
        self.bc.check.queryset_with_pks(model.plan_financing.plans.all(), [1])

        self.assertEqual(
            self.bc.database.list_of("payments.ServiceStockScheduler"),
            [
                service_stock_scheduler_item(
                    {
                        "plan_handler_id": 1,
                        "valid_until": None,
                    }
                ),
            ],
        )

    """
    🔽🔽🔽 With Subscription with one ServiceItem and one Plan with ServiceItem
    """

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.payments.tasks.renew_plan_financing_consumables.delay", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_subscription_with_plan_and_service_item(self):
        subscription = {
            "next_payment_at": UTC_NOW + relativedelta(months=1),
            "plan_expires_at": UTC_NOW + relativedelta(months=2),
            "valid_until": UTC_NOW + relativedelta(months=3),
            "monthly_price": (random.random() * 99.99) + 0.01,
        }
        plan_service_items = [{"plan_id": 1, "service_item_id": n} for n in range(1, 3)] + [
            {"plan_id": 2, "service_item_id": n} for n in range(3, 5)
        ]
        plan = {"is_renewable": False}
        model = self.bc.database.create(
            plan_financing=subscription, plan_service_item=plan_service_items, plan=(2, plan), service_item=4
        )

        # remove prints from mixer
        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        build_service_stock_scheduler_from_plan_financing.delay(1)

        self.assertEqual(self.bc.database.list_of("admissions.Cohort"), [])

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting build_service_stock_scheduler_from_plan_financing for subscription 1"),
            ],
        )
        self.assertEqual(logging.Logger.error.call_args_list, [])

        self.assertEqual(
            self.bc.database.list_of("payments.PlanFinancing"),
            [
                self.bc.format.to_dict(model.plan_financing),
            ],
        )
        self.assertEqual(tasks.renew_plan_financing_consumables.delay.call_args_list, [call(1)])
        self.bc.check.queryset_with_pks(model.plan_financing.plans.all(), [1, 2])

        self.assertEqual(
            self.bc.database.list_of("payments.ServiceStockScheduler"),
            [
                service_stock_scheduler_item(
                    {
                        "id": 1,
                        "plan_handler_id": 1,
                        "valid_until": None,
                    }
                ),
                service_stock_scheduler_item(
                    {
                        "id": 2,
                        "plan_handler_id": 2,
                        "valid_until": None,
                    }
                ),
                service_stock_scheduler_item(
                    {
                        "id": 3,
                        "plan_handler_id": 3,
                        "valid_until": None,
                    }
                ),
                service_stock_scheduler_item(
                    {
                        "id": 4,
                        "plan_handler_id": 4,
                        "valid_until": None,
                    }
                ),
            ],
        )
