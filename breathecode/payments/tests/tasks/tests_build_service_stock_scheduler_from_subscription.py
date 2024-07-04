"""
Test /answer
"""

import logging
import random
from unittest.mock import MagicMock, call, patch

from django.utils import timezone
from breathecode.payments import tasks
from breathecode.payments.actions import calculate_relative_delta

from ...tasks import build_service_stock_scheduler_from_subscription

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
        build_service_stock_scheduler_from_subscription.delay(1)

        self.assertEqual(self.bc.database.list_of("admissions.Cohort"), [])

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting build_service_stock_scheduler_from_subscription for subscription 1"),
                # retrying
                call("Starting build_service_stock_scheduler_from_subscription for subscription 1"),
            ],
        )
        self.assertEqual(
            logging.Logger.error.call_args_list,
            [
                call("Subscription with id 1 not found", exc_info=True),
            ],
        )

        self.assertEqual(self.bc.database.list_of("payments.Subscription"), [])

    """
    🔽🔽🔽 With Subscription
    """

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.payments.tasks.renew_subscription_consumables.delay", MagicMock())
    def test_subscription_exists(self):
        model = self.bc.database.create(subscription=1)

        # remove prints from mixer
        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        build_service_stock_scheduler_from_subscription.delay(1)

        self.assertEqual(self.bc.database.list_of("admissions.Cohort"), [])

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [call("Starting build_service_stock_scheduler_from_subscription for subscription 1")],
        )
        self.assertEqual(logging.Logger.error.call_args_list, [])

        self.assertEqual(
            self.bc.database.list_of("payments.Subscription"),
            [
                self.bc.format.to_dict(model.subscription),
            ],
        )
        self.assertEqual(tasks.renew_subscription_consumables.delay.call_args_list, [call(1)])
        self.bc.check.queryset_with_pks(model.subscription.service_items.all(), [])
        self.bc.check.queryset_with_pks(model.subscription.plans.all(), [])

        self.assertEqual(self.bc.database.list_of("payments.ServiceStockScheduler"), [])

    """
    🔽🔽🔽 With Subscription with one ServiceItem
    """

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.payments.tasks.renew_subscription_consumables.delay", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_subscription_with_service_item(self):
        subscription = {
            "next_payment_at": UTC_NOW + relativedelta(months=1),
            "valid_until": UTC_NOW + relativedelta(months=2),
        }
        model = self.bc.database.create(subscription=subscription, service_item=1, subscription_service_item=1)

        # remove prints from mixer
        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        build_service_stock_scheduler_from_subscription.delay(1)

        self.assertEqual(self.bc.database.list_of("admissions.Cohort"), [])

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting build_service_stock_scheduler_from_subscription for subscription 1"),
            ],
        )
        self.assertEqual(logging.Logger.error.call_args_list, [])

        self.assertEqual(
            self.bc.database.list_of("payments.Subscription"),
            [
                self.bc.format.to_dict(model.subscription),
            ],
        )
        self.assertEqual(tasks.renew_subscription_consumables.delay.call_args_list, [call(1)])
        self.bc.check.queryset_with_pks(model.subscription.service_items.all(), [1])
        self.bc.check.queryset_with_pks(model.subscription.plans.all(), [])

        self.assertEqual(
            self.bc.database.list_of("payments.ServiceStockScheduler"),
            [
                service_stock_scheduler_item(
                    {
                        "valid_until": None,
                        "subscription_handler_id": 1,
                    }
                ),
            ],
        )

    """
    🔽🔽🔽 With Subscription with one Plan with ServiceItem
    """

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.payments.tasks.renew_subscription_consumables.delay", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_subscription_with_plan(self):
        subscription = {
            "next_payment_at": UTC_NOW + relativedelta(months=1),
            "valid_until": UTC_NOW + relativedelta(months=2),
        }

        plan = {"is_renewable": False}

        model = self.bc.database.create(subscription=subscription, plan=plan, plan_service_item=1)

        # remove prints from mixer
        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        build_service_stock_scheduler_from_subscription.delay(1)

        self.assertEqual(self.bc.database.list_of("admissions.Cohort"), [])

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting build_service_stock_scheduler_from_subscription for subscription 1"),
            ],
        )
        self.assertEqual(logging.Logger.error.call_args_list, [])

        self.assertEqual(
            self.bc.database.list_of("payments.Subscription"),
            [
                self.bc.format.to_dict(model.subscription),
            ],
        )
        self.assertEqual(tasks.renew_subscription_consumables.delay.call_args_list, [call(1)])
        self.bc.check.queryset_with_pks(model.subscription.service_items.all(), [])
        self.bc.check.queryset_with_pks(model.subscription.plans.all(), [1])

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
    @patch("breathecode.payments.tasks.renew_subscription_consumables.delay", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_subscription_with_plan_and_service_item(self):
        subscription = {
            "next_payment_at": UTC_NOW + relativedelta(months=1),
            "valid_until": UTC_NOW + relativedelta(months=2),
        }
        subscription_service_items = [{"service_item_id": n} for n in range(1, 3)]
        plan_service_items = [{"plan_id": 1, "service_item_id": n} for n in range(3, 5)] + [
            {"plan_id": 2, "service_item_id": n} for n in range(5, 7)
        ]
        plan = {"is_renewable": False}
        model = self.bc.database.create(
            subscription=subscription,
            subscription_service_item=subscription_service_items,
            plan=(2, plan),
            plan_service_item=plan_service_items,
            service_item=6,
        )

        # remove prints from mixer
        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        build_service_stock_scheduler_from_subscription.delay(1)

        self.assertEqual(self.bc.database.list_of("admissions.Cohort"), [])

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting build_service_stock_scheduler_from_subscription for subscription 1"),
            ],
        )
        self.assertEqual(logging.Logger.error.call_args_list, [])

        self.assertEqual(
            self.bc.database.list_of("payments.Subscription"),
            [
                self.bc.format.to_dict(model.subscription),
            ],
        )
        self.assertEqual(tasks.renew_subscription_consumables.delay.call_args_list, [call(1)])
        self.bc.check.queryset_with_pks(model.subscription.service_items.all(), [1, 2])
        self.bc.check.queryset_with_pks(model.subscription.plans.all(), [1, 2])

        self.assertEqual(
            self.bc.database.list_of("payments.ServiceStockScheduler"),
            [
                service_stock_scheduler_item(
                    {
                        "id": 1,
                        "subscription_handler_id": 1,
                        "valid_until": None,
                    }
                ),
                service_stock_scheduler_item(
                    {
                        "id": 2,
                        "subscription_handler_id": 2,
                        "valid_until": None,
                    }
                ),
                service_stock_scheduler_item(
                    {
                        "id": 3,
                        "plan_handler_id": 1,
                        "valid_until": None,
                    }
                ),
                service_stock_scheduler_item(
                    {
                        "id": 4,
                        "plan_handler_id": 2,
                        "valid_until": None,
                    }
                ),
                service_stock_scheduler_item(
                    {
                        "id": 5,
                        "plan_handler_id": 3,
                        "valid_until": None,
                    }
                ),
                service_stock_scheduler_item(
                    {
                        "id": 6,
                        "plan_handler_id": 4,
                        "valid_until": None,
                    }
                ),
            ],
        )
