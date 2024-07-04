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

from ...tasks import renew_consumables
from ..mixins import PaymentsTestCase

UTC_NOW = timezone.now()


def consumable_item(data={}):
    return {
        "cohort_set_id": None,
        "event_type_set_id": None,
        "how_many": -1,
        "id": 0,
        "mentorship_service_set_id": None,
        "service_item_id": 0,
        "unit_type": "UNIT",
        "user_id": 0,
        "valid_until": UTC_NOW,
        "sort_priority": 1,
        **data,
    }


# FIXME: create_v2 fail in this test file
class PaymentsTestSuite(PaymentsTestCase):
    """
    🔽🔽🔽 ServiceStockScheduler not found
    """

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_scheduler_not_found(self):
        renew_consumables.delay(1)

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting renew_consumables for service stock scheduler 1"),
                # retrying
                call("Starting renew_consumables for service stock scheduler 1"),
            ],
        )
        self.assertEqual(
            logging.Logger.error.call_args_list,
            [
                call("ServiceStockScheduler with id 1 not found", exc_info=True),
            ],
        )

        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])

    """
    🔽🔽🔽 ServiceStockScheduler with PlanFinancing that is over
    """

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_plan_financing_is_over(self):
        plan_financing = {
            "monthly_price": random.random() * 99.99 + 0.01,
            "plan_expires_at": UTC_NOW - relativedelta(seconds=1),
            "valid_until": UTC_NOW - relativedelta(seconds=1),
        }
        plan = {"is_renewable": False}

        model = self.bc.database.create(
            service_stock_scheduler=1, plan=plan, plan_financing=plan_financing, plan_service_item_handler=1
        )

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        renew_consumables.delay(1)

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting renew_consumables for service stock scheduler 1"),
            ],
        )
        self.assertEqual(
            logging.Logger.error.call_args_list,
            [
                call("The plan financing 1 is over", exc_info=True),
            ],
        )

        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])

    """
    🔽🔽🔽 ServiceStockScheduler with PlanFinancing without be paid
    """

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_plan_financing_without_be_paid(self):
        plan_financing = {
            "monthly_price": random.random() * 99.99 + 0.01,
            "plan_expires_at": UTC_NOW + relativedelta(minutes=3),
            "valid_until": UTC_NOW - relativedelta(seconds=1),
        }
        plan = {"is_renewable": False}

        model = self.bc.database.create(
            service_stock_scheduler=1, plan=plan, plan_financing=plan_financing, plan_service_item_handler=1
        )

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        renew_consumables.delay(1)

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting renew_consumables for service stock scheduler 1"),
            ],
        )
        self.assertEqual(
            logging.Logger.error.call_args_list,
            [
                call("The plan financing 1 needs to be paid to renew the consumables", exc_info=True),
            ],
        )

        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])

    """
    🔽🔽🔽 ServiceStockScheduler with PlanFinancing without a PlanServiceItem linked to a resource
    """

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_plan_financing_with_plan_service_item_without_a_resource_linked(self):
        plan_financing = {
            "monthly_price": random.random() * 99.99 + 0.01,
            "plan_expires_at": UTC_NOW + relativedelta(minutes=3),
            "valid_until": UTC_NOW - relativedelta(seconds=1),
            "next_payment_at": UTC_NOW + relativedelta(minutes=3),
        }
        plan = {"is_renewable": False}

        model = self.bc.database.create(
            service_stock_scheduler=1, plan=plan, plan_financing=plan_financing, plan_service_item_handler=1
        )

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        renew_consumables.delay(1)

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting renew_consumables for service stock scheduler 1"),
            ],
        )
        self.assertEqual(
            logging.Logger.error.call_args_list,
            [
                call("The Plan not have a resource linked to it " "for the ServiceStockScheduler 1"),
            ],
        )

        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])

    """
    🔽🔽🔽 ServiceStockScheduler with PlanFinancing with a PlanServiceItem linked to a resource
    """

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_plan_financing_with_plan_service_item_with_two_cohorts_linked(self):
        plan_financing = {
            "monthly_price": random.random() * 99.99 + 0.01,
            "plan_expires_at": UTC_NOW + relativedelta(minutes=5),
            "valid_until": UTC_NOW - relativedelta(seconds=4),
            "next_payment_at": UTC_NOW + relativedelta(minutes=3),
        }
        plan = {"is_renewable": False}
        service_item = {"how_many": -1}
        if random.randint(0, 1) == 1:
            service_item["how_many"] = random.randint(1, 100)
        academy = {"available_as_saas": True}

        model = self.bc.database.create(
            service_stock_scheduler=1,
            plan=plan,
            service_item=service_item,
            plan_financing=plan_financing,
            plan_service_item_handler=1,
            cohort=2,
            cohort_set=2,
            academy=academy,
        )

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        renew_consumables.delay(1)

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting renew_consumables for service stock scheduler 1"),
                call("The consumable 1 for cohort set 1 was built"),
                call("The scheduler 1 was renewed"),
            ],
        )
        self.assertEqual(logging.Logger.error.call_args_list, [])

        self.assertEqual(
            self.bc.database.list_of("payments.Consumable"),
            [
                consumable_item(
                    {
                        "cohort_set_id": 1,
                        "id": 1,
                        "service_item_id": 1,
                        "user_id": 1,
                        "how_many": model.service_item.how_many,
                        "valid_until": UTC_NOW + relativedelta(minutes=5),
                    }
                ),
            ],
        )

    """
    🔽🔽🔽 ServiceStockScheduler with PlanFinancing with a PlanServiceItem linked to a resource
    """

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_plan_financing_with_plan_service_item_with_two_mentorship_services_linked(self):
        plan_financing = {
            "monthly_price": random.random() * 99.99 + 0.01,
            "plan_expires_at": UTC_NOW + relativedelta(minutes=5),
            "valid_until": UTC_NOW - relativedelta(seconds=4),
            "next_payment_at": UTC_NOW + relativedelta(minutes=3),
        }

        service = {"type": "MENTORSHIP_SERVICE_SET"}
        plan = {"is_renewable": False}
        service_item = {"how_many": -1}
        if random.randint(0, 1) == 1:
            service_item["how_many"] = random.randint(1, 100)

        model = self.bc.database.create(
            service_stock_scheduler=1,
            plan=plan,
            service_item=service_item,
            plan_financing=plan_financing,
            plan_service_item_handler=1,
            mentorship_service=2,
            mentorship_service_set=1,
            service=service,
        )

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        renew_consumables.delay(1)

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting renew_consumables for service stock scheduler 1"),
                call("The consumable 1 for mentorship service set 1 was built"),
                call("The scheduler 1 was renewed"),
            ],
        )
        self.assertEqual(logging.Logger.error.call_args_list, [])

        self.assertEqual(
            self.bc.database.list_of("payments.Consumable"),
            [
                consumable_item(
                    {
                        "mentorship_service_set_id": 1,
                        "id": 1,
                        "service_item_id": 1,
                        "user_id": 1,
                        "how_many": model.service_item.how_many,
                        "valid_until": UTC_NOW + relativedelta(minutes=5),
                    }
                ),
            ],
        )

    """
    🔽🔽🔽 ServiceStockScheduler with PlanFinancing, do not needs renew
    """

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_plan_financing_with_plan_service_item__do_not_needs_renew(self):
        plan_financing = {
            "monthly_price": random.random() * 99.99 + 0.01,
            "plan_expires_at": UTC_NOW + relativedelta(minutes=5),
            "valid_until": UTC_NOW - relativedelta(seconds=4),
            "next_payment_at": UTC_NOW + relativedelta(minutes=3),
        }

        service_stock_scheduler = {
            "valid_until": UTC_NOW - relativedelta(seconds=1),
        }
        plan = {"is_renewable": False}

        model = self.bc.database.create(
            service_stock_scheduler=service_stock_scheduler,
            plan=plan,
            plan_financing=plan_financing,
            plan_service_item_handler=1,
            mentorship_service=2,
            mentorship_service_set=1,
        )

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        renew_consumables.delay(1)

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting renew_consumables for service stock scheduler 1"),
                call("The scheduler 1 don't needs to be renewed"),
            ],
        )
        self.assertEqual(logging.Logger.error.call_args_list, [])

        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])

    """
    🔽🔽🔽 ServiceStockScheduler with Subscription that is over
    """

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_subscription__plan__is_over(self):
        subscription = {
            "monthly_price": random.random() * 99.99 + 0.01,
            "plan_expires_at": UTC_NOW - relativedelta(seconds=1),
            "valid_until": UTC_NOW - relativedelta(seconds=1),
        }
        plan = {"is_renewable": False}

        model = self.bc.database.create(
            service_stock_scheduler=1, plan=plan, subscription=subscription, plan_service_item_handler=1
        )

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        renew_consumables.delay(1)

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting renew_consumables for service stock scheduler 1"),
            ],
        )
        self.assertEqual(
            logging.Logger.error.call_args_list,
            [
                call("The subscription 1 is over", exc_info=True),
            ],
        )

        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])

    """
    🔽🔽🔽 ServiceStockScheduler with Subscription without be paid
    """

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_subscription__plan__without_be_paid(self):
        subscription = {
            "monthly_price": random.random() * 99.99 + 0.01,
            "plan_expires_at": UTC_NOW - relativedelta(seconds=1),
            "valid_until": UTC_NOW + relativedelta(minutes=3),
        }
        plan = {"is_renewable": False}

        model = self.bc.database.create(
            service_stock_scheduler=1, plan=plan, subscription=subscription, plan_service_item_handler=1
        )

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        renew_consumables.delay(1)

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting renew_consumables for service stock scheduler 1"),
            ],
        )
        self.assertEqual(
            logging.Logger.error.call_args_list,
            [
                call("The subscription 1 needs to be paid to renew the consumables", exc_info=True),
            ],
        )

        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])

    """
    🔽🔽🔽 ServiceStockScheduler with Subscription without a PlanServiceItem linked to a resource
    """

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_subscription__plan__with_plan_service_item_without_a_resource_linked(self):
        subscription = {
            "monthly_price": random.random() * 99.99 + 0.01,
            "plan_expires_at": UTC_NOW - relativedelta(seconds=1),
            "valid_until": UTC_NOW + relativedelta(minutes=3),
            "next_payment_at": UTC_NOW + relativedelta(minutes=3),
        }
        plan = {"is_renewable": False}

        model = self.bc.database.create(
            service_stock_scheduler=1, plan=plan, subscription=subscription, plan_service_item_handler=1
        )

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        renew_consumables.delay(1)

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting renew_consumables for service stock scheduler 1"),
            ],
        )
        self.assertEqual(
            logging.Logger.error.call_args_list,
            [
                call("The Plan not have a resource linked to it " "for the ServiceStockScheduler 1"),
            ],
        )

        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])

    """
    🔽🔽🔽 ServiceStockScheduler with Subscription with a PlanServiceItem linked to a resource
    """

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_subscription__plan__with_plan_service_item_with_two_cohorts_linked(self):
        subscription = {
            "monthly_price": random.random() * 99.99 + 0.01,
            "plan_expires_at": UTC_NOW - relativedelta(seconds=4),
            "valid_until": UTC_NOW + relativedelta(minutes=5),
            "next_payment_at": UTC_NOW + relativedelta(minutes=3),
        }
        plan = {"is_renewable": False}
        service_item = {"how_many": -1}
        if random.randint(0, 1) == 1:
            service_item["how_many"] = random.randint(1, 100)
        academy = {"available_as_saas": True}

        model = self.bc.database.create(
            service_stock_scheduler=1,
            plan=plan,
            service_item=service_item,
            subscription=subscription,
            plan_service_item_handler=1,
            cohort=2,
            cohort_set=2,
            academy=academy,
        )

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        renew_consumables.delay(1)

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting renew_consumables for service stock scheduler 1"),
                call("The consumable 1 for cohort set 1 was built"),
                call("The scheduler 1 was renewed"),
            ],
        )
        self.assertEqual(logging.Logger.error.call_args_list, [])

        self.assertEqual(
            self.bc.database.list_of("payments.Consumable"),
            [
                consumable_item(
                    {
                        "cohort_set_id": 1,
                        "id": 1,
                        "service_item_id": 1,
                        "user_id": 1,
                        "how_many": model.service_item.how_many,
                        "valid_until": UTC_NOW + relativedelta(minutes=5),
                    }
                ),
            ],
        )

    """
    🔽🔽🔽 ServiceStockScheduler with Subscription with a PlanServiceItem linked to a resource
    """

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_subscription__plan__with_plan_service_item_with_two_mentorship_services_linked(self):
        subscription = {
            "monthly_price": random.random() * 99.99 + 0.01,
            "plan_expires_at": UTC_NOW - relativedelta(seconds=4),
            "valid_until": UTC_NOW + relativedelta(minutes=5),
            "next_payment_at": UTC_NOW + relativedelta(minutes=3),
        }

        service = {"type": "MENTORSHIP_SERVICE_SET"}
        plan = {"is_renewable": False}
        service_item = {"how_many": -1}
        if random.randint(0, 1) == 1:
            service_item["how_many"] = random.randint(1, 100)

        model = self.bc.database.create(
            service_stock_scheduler=1,
            plan=plan,
            service_item=service_item,
            subscription=subscription,
            plan_service_item_handler=1,
            mentorship_service=2,
            mentorship_service_set=1,
            service=service,
        )

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        renew_consumables.delay(1)

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting renew_consumables for service stock scheduler 1"),
                call("The consumable 1 for mentorship service set 1 was built"),
                call("The scheduler 1 was renewed"),
            ],
        )
        self.assertEqual(logging.Logger.error.call_args_list, [])

        self.assertEqual(
            self.bc.database.list_of("payments.Consumable"),
            [
                consumable_item(
                    {
                        "mentorship_service_set_id": 1,
                        "id": 1,
                        "service_item_id": 1,
                        "user_id": 1,
                        "how_many": model.service_item.how_many,
                        "valid_until": UTC_NOW + relativedelta(minutes=5),
                    }
                ),
            ],
        )

    """
    🔽🔽🔽 ServiceStockScheduler with Subscription, do not needs renew
    """

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_subscription__plan__with_plan_service_item__do_not_needs_renew(self):
        subscription = {
            "monthly_price": random.random() * 99.99 + 0.01,
            "plan_expires_at": UTC_NOW - relativedelta(seconds=4),
            "valid_until": UTC_NOW + relativedelta(minutes=5),
            "next_payment_at": UTC_NOW + relativedelta(minutes=3),
        }

        service_stock_scheduler = {
            "valid_until": UTC_NOW - relativedelta(seconds=1),
        }
        plan = {"is_renewable": False}

        model = self.bc.database.create(
            service_stock_scheduler=service_stock_scheduler,
            plan=plan,
            subscription=subscription,
            plan_service_item_handler=1,
            mentorship_service=2,
            mentorship_service_set=1,
        )

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        renew_consumables.delay(1)

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting renew_consumables for service stock scheduler 1"),
                call("The scheduler 1 don't needs to be renewed"),
            ],
        )
        self.assertEqual(logging.Logger.error.call_args_list, [])

        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])

    """
    🔽🔽🔽 ServiceStockScheduler with PlanFinancing that is over
    """

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_subscription__service_item__is_over(self):
        subscription = {
            "monthly_price": random.random() * 99.99 + 0.01,
            "plan_expires_at": UTC_NOW - relativedelta(seconds=1),
            "valid_until": UTC_NOW - relativedelta(seconds=1),
        }
        plan = {"is_renewable": False}

        model = self.bc.database.create(
            service_stock_scheduler=1, plan=plan, subscription=subscription, subscription_service_item=1
        )

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        renew_consumables.delay(1)

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting renew_consumables for service stock scheduler 1"),
            ],
        )
        self.assertEqual(
            logging.Logger.error.call_args_list,
            [
                call("The subscription 1 is over", exc_info=True),
            ],
        )

        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])

    """
    🔽🔽🔽 ServiceStockScheduler with PlanFinancing without be paid
    """

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_subscription__service_item__without_be_paid(self):
        subscription = {
            "monthly_price": random.random() * 99.99 + 0.01,
            "plan_expires_at": UTC_NOW - relativedelta(seconds=1),
            "valid_until": UTC_NOW + relativedelta(minutes=3),
        }

        model = self.bc.database.create(
            service_stock_scheduler=1, subscription=subscription, subscription_service_item=1
        )

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        renew_consumables.delay(1)

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting renew_consumables for service stock scheduler 1"),
            ],
        )
        self.assertEqual(
            logging.Logger.error.call_args_list,
            [
                call("The subscription 1 needs to be paid to renew the consumables", exc_info=True),
            ],
        )

        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])

    """
    🔽🔽🔽 ServiceStockScheduler with PlanFinancing without a PlanServiceItem linked to a resource
    """

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_subscription__service_item__with_plan_service_item_without_a_resource_linked(self):
        subscription = {
            "monthly_price": random.random() * 99.99 + 0.01,
            "plan_expires_at": UTC_NOW - relativedelta(seconds=1),
            "valid_until": UTC_NOW + relativedelta(minutes=3),
            "next_payment_at": UTC_NOW + relativedelta(minutes=3),
        }

        model = self.bc.database.create(
            service_stock_scheduler=1, subscription=subscription, subscription_service_item=1
        )

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        renew_consumables.delay(1)

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting renew_consumables for service stock scheduler 1"),
            ],
        )
        self.assertEqual(
            logging.Logger.error.call_args_list,
            [
                call("The Plan not have a resource linked to it " "for the ServiceStockScheduler 1"),
            ],
        )

        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])

    """
    🔽🔽🔽 ServiceStockScheduler with PlanFinancing with a PlanServiceItem linked to a resource
    """

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_subscription__service_item__with_plan_service_item_with_two_cohorts_linked(self):
        subscription = {
            "monthly_price": random.random() * 99.99 + 0.01,
            "plan_expires_at": UTC_NOW - relativedelta(seconds=2),
            "valid_until": UTC_NOW + relativedelta(minutes=3),
            "next_payment_at": UTC_NOW + relativedelta(minutes=3),
        }

        service_item = {"how_many": -1}
        if random.randint(0, 1) == 1:
            service_item["how_many"] = random.randint(1, 100)
        academy = {"available_as_saas": True}

        model = self.bc.database.create(
            service_stock_scheduler=1,
            service_item=service_item,
            subscription=subscription,
            subscription_service_item=1,
            cohort=2,
            cohort_set=2,
            academy=academy,
        )

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        renew_consumables.delay(1)

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting renew_consumables for service stock scheduler 1"),
                call("The consumable 1 for cohort set 1 was built"),
                call("The scheduler 1 was renewed"),
            ],
        )
        self.assertEqual(logging.Logger.error.call_args_list, [])

        self.assertEqual(
            self.bc.database.list_of("payments.Consumable"),
            [
                consumable_item(
                    {
                        "cohort_set_id": 1,
                        "id": 1,
                        "service_item_id": 1,
                        "user_id": 1,
                        "how_many": model.service_item.how_many,
                        "valid_until": UTC_NOW + relativedelta(minutes=3),
                    }
                ),
            ],
        )

    """
    🔽🔽🔽 ServiceStockScheduler with PlanFinancing with a PlanServiceItem linked to a resource
    """

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_subscription__service_item__with_plan_service_item_with_two_mentorship_services_linked(self):
        subscription = {
            "monthly_price": random.random() * 99.99 + 0.01,
            "plan_expires_at": UTC_NOW - relativedelta(seconds=2),
            "valid_until": UTC_NOW + relativedelta(minutes=3),
            "next_payment_at": UTC_NOW + relativedelta(minutes=3),
        }

        service = {"type": "MENTORSHIP_SERVICE_SET"}
        service_item = {"how_many": -1}
        if random.randint(0, 1) == 1:
            service_item["how_many"] = random.randint(1, 100)

        model = self.bc.database.create(
            service_stock_scheduler=1,
            service_item=service_item,
            subscription=subscription,
            subscription_service_item=1,
            mentorship_service=2,
            mentorship_service_set=1,
            service=service,
        )

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        renew_consumables.delay(1)

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting renew_consumables for service stock scheduler 1"),
                call("The consumable 1 for mentorship service set 1 was built"),
                call("The scheduler 1 was renewed"),
            ],
        )
        self.assertEqual(logging.Logger.error.call_args_list, [])

        self.assertEqual(
            self.bc.database.list_of("payments.Consumable"),
            [
                consumable_item(
                    {
                        "mentorship_service_set_id": 1,
                        "id": 1,
                        "service_item_id": 1,
                        "user_id": 1,
                        "how_many": model.service_item.how_many,
                        "valid_until": UTC_NOW + relativedelta(minutes=3),
                    }
                ),
            ],
        )

    """
    🔽🔽🔽 ServiceStockScheduler with PlanFinancing, do not needs renew
    """

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_subscription__service_item__with_plan_service_item__do_not_needs_renew(self):
        subscription = {
            "monthly_price": random.random() * 99.99 + 0.01,
            "plan_expires_at": UTC_NOW - relativedelta(seconds=2),
            "valid_until": UTC_NOW + relativedelta(minutes=3),
            "next_payment_at": UTC_NOW + relativedelta(minutes=3),
        }

        service_stock_scheduler = {
            "valid_until": UTC_NOW - relativedelta(seconds=1),
        }

        model = self.bc.database.create(
            service_stock_scheduler=service_stock_scheduler,
            subscription=subscription,
            subscription_service_item=1,
            mentorship_service=2,
            mentorship_service_set=1,
        )

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        renew_consumables.delay(1)

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting renew_consumables for service stock scheduler 1"),
                call("The scheduler 1 don't needs to be renewed"),
            ],
        )
        self.assertEqual(logging.Logger.error.call_args_list, [])

        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
