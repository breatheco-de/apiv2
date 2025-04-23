"""
Test /answer
"""

import logging
import random
from datetime import timedelta
from datetime import timezone as dt_timezone
from unittest.mock import MagicMock, call, patch

import pytest
from capyc import pytest as capyc
from dateutil.relativedelta import relativedelta
from django.utils import timezone

import breathecode.activity.tasks as activity_tasks
from breathecode.payments import tasks

from ...tasks import build_subscription
from ..mixins import PaymentsTestCase

UTC_NOW = timezone.now()


def subscription_item(data={}):
    return {
        "id": 1,
        "selected_cohort_set_id": None,
        "selected_event_type_set_id": None,
        "selected_mentorship_service_set_id": None,
        "academy_id": 1,
        "is_refundable": True,
        "paid_at": UTC_NOW,
        "pay_every": 1,
        "pay_every_unit": "MONTH",
        "status": "ACTIVE",
        "status_message": None,
        "user_id": 1,
        "valid_until": UTC_NOW,
        "next_payment_at": UTC_NOW,
        "externally_managed": False,
        "country_code": "",
        "currency_id": 1,
        "conversion_info": None,
        **data,
    }


@pytest.fixture(autouse=True)
def setup(monkeypatch):
    monkeypatch.setattr(activity_tasks.add_activity, "delay", MagicMock())
    yield


def assert_subscription_with_no_service_items(subscription):
    assert subscription.service_items.count() == 0


# FIXME: create_v2 fail in this test file
class PaymentsTestSuite(PaymentsTestCase):
    """
    🔽🔽🔽 Bag not found
    """

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    def test_bag_not_found(self):
        build_subscription.delay(1, 1)

        self.assertEqual(self.bc.database.list_of("admissions.Cohort"), [])

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting build_subscription for bag 1"),
                # retrying
                call("Starting build_subscription for bag 1"),
            ],
        )
        self.assertEqual(
            logging.Logger.error.call_args_list,
            [
                call("Bag with id 1 not found", exc_info=True),
            ],
        )

        self.assertEqual(self.bc.database.list_of("payments.Bag"), [])
        self.assertEqual(self.bc.database.list_of("payments.Invoice"), [])
        self.assertEqual(self.bc.database.list_of("payments.Subscription"), [])
        self.bc.check.calls(activity_tasks.add_activity.delay.call_args_list, [])
        assert self.bc.database.list_of("task_manager.ScheduledTask") == []

    """
    🔽🔽🔽 With Bag
    """

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    def test_invoice_not_found(self):
        bag = {"status": "PAID", "was_delivered": False}
        model = self.bc.database.create_v2(bag=bag)

        # remove prints from mixer
        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        build_subscription.delay(1, 1)

        self.assertEqual(self.bc.database.list_of("admissions.Cohort"), [])

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting build_subscription for bag 1"),
                # retrying
                call("Starting build_subscription for bag 1"),
            ],
        )
        self.assertEqual(
            logging.Logger.error.call_args_list,
            [
                call("Invoice with id 1 not found", exc_info=True),
            ],
        )

        self.assertEqual(self.bc.database.list_of("payments.Bag"), [self.bc.format.to_dict(model.bag)])
        self.assertEqual(self.bc.database.list_of("payments.Invoice"), [])
        self.assertEqual(self.bc.database.list_of("payments.Subscription"), [])
        self.bc.check.calls(
            activity_tasks.add_activity.delay.call_args_list,
            [
                call(1, "bag_created", related_type="payments.Bag", related_id=1),
            ],
        )
        assert self.bc.database.list_of("task_manager.ScheduledTask") == []

    """
    🔽🔽🔽 With Bag and Invoice
    """

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch.object(timezone, "now", MagicMock(return_value=UTC_NOW))
    @patch("breathecode.payments.tasks.build_service_stock_scheduler_from_subscription.delay", MagicMock())
    def test_subscription_was_created(self):
        bag = {
            "status": "PAID",
            "was_delivered": False,
            "chosen_period": random.choice(["MONTH", "QUARTER", "HALF", "YEAR"]),
        }
        invoice = {"status": "FULFILLED"}
        months = 1

        if bag["chosen_period"] == "QUARTER":
            months = 3

        elif bag["chosen_period"] == "HALF":
            months = 6

        elif bag["chosen_period"] == "YEAR":
            months = 12

        model = self.bc.database.create(bag=bag, invoice=invoice)

        # remove prints from mixer
        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        build_subscription.delay(1, 1)

        self.assertEqual(self.bc.database.list_of("admissions.Cohort"), [])

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting build_subscription for bag 1"),
                call("Subscription was created with id 1"),
            ],
        )
        self.assertEqual(logging.Logger.error.call_args_list, [])

        self.assertEqual(
            self.bc.database.list_of("payments.Bag"),
            [
                {
                    **self.bc.format.to_dict(model.bag),
                    "was_delivered": True,
                },
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("payments.Invoice"),
            [
                self.bc.format.to_dict(model.invoice),
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("payments.Subscription"),
            [
                subscription_item(
                    {
                        "conversion_info": None,
                        "paid_at": model.invoice.paid_at,
                        "valid_until": None,
                        "next_payment_at": model.invoice.paid_at + relativedelta(months=months),
                        "pay_every": months if months != 12 else 1,
                        "pay_every_unit": "MONTH" if months != 12 else "YEAR",
                    }
                ),
            ],
        )

        self.assertEqual(
            tasks.build_service_stock_scheduler_from_subscription.delay.call_args_list,
            [
                call(1),
            ],
        )
        self.bc.check.calls(
            activity_tasks.add_activity.delay.call_args_list,
            [
                call(1, "bag_created", related_type="payments.Bag", related_id=1),
            ],
        )
        delta = timedelta(days=(model.invoice.paid_at + relativedelta(months=months) - model.invoice.paid_at).days)
        assert self.bc.database.list_of("task_manager.ScheduledTask") == [
            {
                "task_name": "charge_subscription",
                "task_module": "breathecode.payments.tasks",
                "arguments": {
                    "args": [1],
                    "kwargs": {},
                },
                "duration": delta,
                "eta": UTC_NOW + delta,
                "status": "PENDING",
                "id": 1,
            },
        ]
        assert_subscription_with_no_service_items(self.bc.database.get("payments.Subscription", 1, dict=False))

    """
    🔽🔽🔽 With Bag and Invoice and conversion_info
    """

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch.object(timezone, "now", MagicMock(return_value=UTC_NOW))
    @patch("breathecode.payments.tasks.build_service_stock_scheduler_from_subscription.delay", MagicMock())
    def test_subscription_was_created_with_conversion_info(self):
        bag = {
            "status": "PAID",
            "was_delivered": False,
            "chosen_period": random.choice(["MONTH", "QUARTER", "HALF", "YEAR"]),
        }
        invoice = {"status": "FULFILLED"}
        months = 1

        if bag["chosen_period"] == "QUARTER":
            months = 3

        elif bag["chosen_period"] == "HALF":
            months = 6

        elif bag["chosen_period"] == "YEAR":
            months = 12

        model = self.bc.database.create(bag=bag, invoice=invoice)

        # remove prints from mixer
        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        conversion_info = "{ 'landing_url': '/home' }"
        build_subscription.delay(1, 1, conversion_info=conversion_info)

        self.assertEqual(self.bc.database.list_of("admissions.Cohort"), [])

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting build_subscription for bag 1"),
                call("Subscription was created with id 1"),
            ],
        )
        self.assertEqual(logging.Logger.error.call_args_list, [])

        self.assertEqual(
            self.bc.database.list_of("payments.Bag"),
            [
                {
                    **self.bc.format.to_dict(model.bag),
                    "was_delivered": True,
                },
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("payments.Invoice"),
            [
                self.bc.format.to_dict(model.invoice),
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("payments.Subscription"),
            [
                subscription_item(
                    {
                        "conversion_info": {"landing_url": "/home"},
                        "paid_at": model.invoice.paid_at,
                        "valid_until": None,
                        "next_payment_at": model.invoice.paid_at + relativedelta(months=months),
                        "pay_every": months if months != 12 else 1,
                        "pay_every_unit": "MONTH" if months != 12 else "YEAR",
                    }
                ),
            ],
        )

        self.assertEqual(
            tasks.build_service_stock_scheduler_from_subscription.delay.call_args_list,
            [
                call(1),
            ],
        )
        self.bc.check.calls(
            activity_tasks.add_activity.delay.call_args_list,
            [
                call(1, "bag_created", related_type="payments.Bag", related_id=1),
            ],
        )
        delta = timedelta(days=(model.invoice.paid_at + relativedelta(months=months) - model.invoice.paid_at).days)
        assert self.bc.database.list_of("task_manager.ScheduledTask") == [
            {
                "task_name": "charge_subscription",
                "task_module": "breathecode.payments.tasks",
                "arguments": {
                    "args": [1],
                    "kwargs": {},
                },
                "duration": delta,
                "eta": UTC_NOW + delta,
                "status": "PENDING",
                "id": 1,
            },
        ]
        assert_subscription_with_no_service_items(self.bc.database.get("payments.Subscription", 1, dict=False))

    """
    🔽🔽🔽 With Bag, Invoice and Cohort
    """

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch.object(timezone, "now", MagicMock(return_value=UTC_NOW))
    @patch("breathecode.payments.tasks.build_service_stock_scheduler_from_subscription.delay", MagicMock())
    def test_subscription_was_created__bag_with_cohort(self):
        bag = {
            "status": "PAID",
            "was_delivered": False,
            "chosen_period": random.choice(["MONTH", "QUARTER", "HALF", "YEAR"]),
        }
        invoice = {"status": "FULFILLED"}
        months = 1

        if bag["chosen_period"] == "QUARTER":
            months = 3

        elif bag["chosen_period"] == "HALF":
            months = 6

        elif bag["chosen_period"] == "YEAR":
            months = 12

        plan = {
            "time_of_life": None,
            "time_of_life_unit": None,
        }
        academy = {"available_as_saas": True}
        model = self.bc.database.create(bag=bag, invoice=invoice, cohort_set=1, plan=plan, academy=academy)

        # remove prints from mixer
        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        build_subscription.delay(1, 1)

        self.assertEqual(
            self.bc.database.list_of("admissions.Cohort"),
            [
                self.bc.format.to_dict(model.cohort),
            ],
        )

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting build_subscription for bag 1"),
                call("Subscription was created with id 1"),
            ],
        )
        self.assertEqual(logging.Logger.error.call_args_list, [])

        self.assertEqual(
            self.bc.database.list_of("payments.Bag"),
            [
                {
                    **self.bc.format.to_dict(model.bag),
                    "was_delivered": True,
                },
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("payments.Invoice"),
            [
                self.bc.format.to_dict(model.invoice),
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("payments.Subscription"),
            [
                subscription_item(
                    {
                        "conversion_info": None,
                        "paid_at": model.invoice.paid_at,
                        "valid_until": None,
                        "selected_cohort_set_id": 1,
                        "next_payment_at": model.invoice.paid_at + relativedelta(months=months),
                        "pay_every": months if months != 12 else 1,
                        "pay_every_unit": "MONTH" if months != 12 else "YEAR",
                    }
                ),
            ],
        )

        self.assertEqual(
            tasks.build_service_stock_scheduler_from_subscription.delay.call_args_list,
            [
                call(1),
            ],
        )
        self.bc.check.calls(
            activity_tasks.add_activity.delay.call_args_list,
            [
                call(1, "bag_created", related_type="payments.Bag", related_id=1),
            ],
        )
        delta = timedelta(days=(model.invoice.paid_at + relativedelta(months=months) - model.invoice.paid_at).days)
        assert self.bc.database.list_of("task_manager.ScheduledTask") == [
            {
                "task_name": "charge_subscription",
                "task_module": "breathecode.payments.tasks",
                "arguments": {
                    "args": [1],
                    "kwargs": {},
                },
                "duration": delta,
                "eta": UTC_NOW + delta,
                "status": "PENDING",
                "id": 1,
            },
        ]
        assert_subscription_with_no_service_items(self.bc.database.get("payments.Subscription", 1, dict=False))

    """
    🔽🔽🔽 With Bag, Invoice and EventTypeSet
    """

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch.object(timezone, "now", MagicMock(return_value=UTC_NOW))
    @patch("breathecode.payments.tasks.build_service_stock_scheduler_from_subscription.delay", MagicMock())
    def test_subscription_was_created__bag_with_event_type_set(self):
        bag = {
            "status": "PAID",
            "was_delivered": False,
            "chosen_period": random.choice(["MONTH", "QUARTER", "HALF", "YEAR"]),
        }
        invoice = {"status": "FULFILLED"}
        months = 1

        if bag["chosen_period"] == "QUARTER":
            months = 3

        elif bag["chosen_period"] == "HALF":
            months = 6

        elif bag["chosen_period"] == "YEAR":
            months = 12

        plan = {
            "time_of_life": None,
            "time_of_life_unit": None,
        }
        model = self.bc.database.create(bag=bag, invoice=invoice, event_type_set=1, plan=plan)

        # remove prints from mixer
        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        build_subscription.delay(1, 1)

        self.assertEqual(self.bc.database.list_of("admissions.Cohort"), [])

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting build_subscription for bag 1"),
                call("Subscription was created with id 1"),
            ],
        )
        self.assertEqual(logging.Logger.error.call_args_list, [])

        self.assertEqual(
            self.bc.database.list_of("payments.Bag"),
            [
                {
                    **self.bc.format.to_dict(model.bag),
                    "was_delivered": True,
                },
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("payments.Invoice"),
            [
                self.bc.format.to_dict(model.invoice),
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("payments.Subscription"),
            [
                subscription_item(
                    {
                        "conversion_info": None,
                        "paid_at": model.invoice.paid_at,
                        "valid_until": None,
                        "selected_event_type_set_id": 1,
                        "next_payment_at": model.invoice.paid_at + relativedelta(months=months),
                        "pay_every": months if months != 12 else 1,
                        "pay_every_unit": "MONTH" if months != 12 else "YEAR",
                    }
                ),
            ],
        )

        self.assertEqual(
            tasks.build_service_stock_scheduler_from_subscription.delay.call_args_list,
            [
                call(1),
            ],
        )
        self.bc.check.calls(
            activity_tasks.add_activity.delay.call_args_list,
            [
                call(1, "bag_created", related_type="payments.Bag", related_id=1),
            ],
        )
        delta = timedelta(days=(model.invoice.paid_at + relativedelta(months=months) - model.invoice.paid_at).days)
        assert self.bc.database.list_of("task_manager.ScheduledTask") == [
            {
                "task_name": "charge_subscription",
                "task_module": "breathecode.payments.tasks",
                "arguments": {
                    "args": [1],
                    "kwargs": {},
                },
                "duration": delta,
                "eta": UTC_NOW + delta,
                "status": "PENDING",
                "id": 1,
            },
        ]
        assert_subscription_with_no_service_items(self.bc.database.get("payments.Subscription", 1, dict=False))

    """
    🔽🔽🔽 With Bag, Invoice and MentorshipServiceSet
    """

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch.object(timezone, "now", MagicMock(return_value=UTC_NOW))
    @patch("breathecode.payments.tasks.build_service_stock_scheduler_from_subscription.delay", MagicMock())
    def test_subscription_was_created__bag_with_mentorship_service_set(self):
        bag = {
            "status": "PAID",
            "was_delivered": False,
            "chosen_period": random.choice(["MONTH", "QUARTER", "HALF", "YEAR"]),
        }
        invoice = {"status": "FULFILLED"}
        months = 1

        if bag["chosen_period"] == "QUARTER":
            months = 3

        elif bag["chosen_period"] == "HALF":
            months = 6

        elif bag["chosen_period"] == "YEAR":
            months = 12

        plan = {
            "time_of_life": None,
            "time_of_life_unit": None,
        }
        model = self.bc.database.create(bag=bag, invoice=invoice, mentorship_service_set=1, plan=plan)

        # remove prints from mixer
        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        build_subscription.delay(1, 1)

        self.assertEqual(self.bc.database.list_of("admissions.Cohort"), [])

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting build_subscription for bag 1"),
                call("Subscription was created with id 1"),
            ],
        )
        self.assertEqual(logging.Logger.error.call_args_list, [])

        self.assertEqual(
            self.bc.database.list_of("payments.Bag"),
            [
                {
                    **self.bc.format.to_dict(model.bag),
                    "was_delivered": True,
                },
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("payments.Invoice"),
            [
                self.bc.format.to_dict(model.invoice),
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("payments.Subscription"),
            [
                subscription_item(
                    {
                        "conversion_info": None,
                        "paid_at": model.invoice.paid_at,
                        "valid_until": None,
                        "selected_mentorship_service_set_id": 1,
                        "next_payment_at": model.invoice.paid_at + relativedelta(months=months),
                        "pay_every": months if months != 12 else 1,
                        "pay_every_unit": "MONTH" if months != 12 else "YEAR",
                    }
                ),
            ],
        )

        self.assertEqual(
            tasks.build_service_stock_scheduler_from_subscription.delay.call_args_list,
            [
                call(1),
            ],
        )
        self.bc.check.calls(
            activity_tasks.add_activity.delay.call_args_list,
            [
                call(1, "bag_created", related_type="payments.Bag", related_id=1),
            ],
        )
        delta = timedelta(days=(model.invoice.paid_at + relativedelta(months=months) - model.invoice.paid_at).days)
        assert self.bc.database.list_of("task_manager.ScheduledTask") == [
            {
                "task_name": "charge_subscription",
                "task_module": "breathecode.payments.tasks",
                "arguments": {
                    "args": [1],
                    "kwargs": {},
                },
                "duration": delta,
                "eta": UTC_NOW + delta,
                "status": "PENDING",
                "id": 1,
            },
        ]
        assert_subscription_with_no_service_items(self.bc.database.get("payments.Subscription", 1, dict=False))

    """
    🔽🔽🔽 With Bag with service items
    """

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch.object(timezone, "now", MagicMock(return_value=UTC_NOW))
    @patch("breathecode.payments.tasks.build_service_stock_scheduler_from_subscription.delay", MagicMock())
    def test_subscription_was_created__bag_with_service_items(self):
        bag = {
            "status": "PAID",
            "was_delivered": False,
            "chosen_period": random.choice(["MONTH", "QUARTER", "HALF", "YEAR"]),
        }
        invoice = {"status": "FULFILLED"}
        months = 1

        if bag["chosen_period"] == "QUARTER":
            months = 3

        elif bag["chosen_period"] == "HALF":
            months = 6

        elif bag["chosen_period"] == "YEAR":
            months = 12

        plan = {
            "time_of_life": None,
            "time_of_life_unit": None,
        }
        model = self.bc.database.create(bag=bag, invoice=invoice, plan=plan, service_items=2)

        # remove prints from mixer
        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        build_subscription.delay(1, 1)

        self.assertEqual(self.bc.database.list_of("admissions.Cohort"), [])

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting build_subscription for bag 1"),
                call("Subscription was created with id 1"),
            ],
        )
        self.assertEqual(logging.Logger.error.call_args_list, [])

        self.assertEqual(
            self.bc.database.list_of("payments.Bag"),
            [
                {
                    **self.bc.format.to_dict(model.bag),
                    "was_delivered": True,
                },
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("payments.Invoice"),
            [
                self.bc.format.to_dict(model.invoice),
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("payments.Subscription"),
            [
                subscription_item(
                    {
                        "conversion_info": None,
                        "paid_at": model.invoice.paid_at,
                        "valid_until": None,
                        "next_payment_at": model.invoice.paid_at + relativedelta(months=months),
                        "pay_every": months if months != 12 else 1,
                        "pay_every_unit": "MONTH" if months != 12 else "YEAR",
                    }
                ),
            ],
        )

        self.assertEqual(
            tasks.build_service_stock_scheduler_from_subscription.delay.call_args_list,
            [
                call(1),
            ],
        )
        self.bc.check.calls(
            activity_tasks.add_activity.delay.call_args_list,
            [
                call(1, "bag_created", related_type="payments.Bag", related_id=1),
            ],
        )
        assert_subscription_with_no_service_items(self.bc.database.get("payments.Subscription", 1, dict=False))


@pytest.mark.parametrize(
    "chosen_period,expected_months,expected_pay_every,expected_pay_every_unit",
    [
        ("MONTH", 1, 1, "MONTH"),
        ("QUARTER", 3, 3, "MONTH"),
        ("HALF", 6, 6, "MONTH"),
        ("YEAR", 12, 1, "YEAR"),
    ],
)
def test_build_subscription_with_different_chosen_periods(
    database: capyc.Database,
    monkeypatch,
    chosen_period,
    expected_months,
    expected_pay_every,
    expected_pay_every_unit,
    format: capyc.Format,
):
    """Test build_subscription with different chosen periods"""
    from breathecode.payments import tasks

    # Arrange
    utc_now = timezone.now()

    logger_info = MagicMock()
    monkeypatch.setattr("logging.Logger.info", logger_info)

    logger_error = MagicMock()
    monkeypatch.setattr("logging.Logger.error", logger_error)

    build_scheduler = MagicMock()
    monkeypatch.setattr(
        "breathecode.payments.tasks.build_service_stock_scheduler_from_subscription.delay", build_scheduler
    )

    # Create test data
    bag = {"status": "PAID", "was_delivered": False, "chosen_period": chosen_period}
    invoice = {"status": "FULFILLED"}
    model = database.create(invoice=invoice, bag=bag, city=1, country=1)

    # Act
    tasks.build_subscription.delay(model.bag.id, model.invoice.id, start_date=utc_now)

    # Assert
    assert database.list_of("payments.Subscription") == [
        {
            "conversion_info": None,
            "academy_id": 1,
            "paid_at": model.invoice.paid_at.replace(tzinfo=dt_timezone.utc),
            "valid_until": None,
            "next_payment_at": (utc_now + relativedelta(months=expected_months)).replace(tzinfo=dt_timezone.utc),
            "pay_every": expected_pay_every,
            "pay_every_unit": expected_pay_every_unit,
            "externally_managed": False,
            "id": 1,
            "is_refundable": True,
            "selected_cohort_set_id": None,
            "selected_event_type_set_id": None,
            "selected_mentorship_service_set_id": None,
            "status": "ACTIVE",
            "status_message": None,
            "user_id": 1,
            "country_code": "",
            "currency_id": 1,
        }
    ]

    # Check that the invoice is linked to the subscription
    assert database.list_of("payments.Invoice") == [{**format.to_obj_repr(model.invoice)}]

    # Check that the bag was marked as delivered
    assert database.list_of("payments.Bag") == [{**format.to_obj_repr(model.bag), "was_delivered": True}]

    # Verify logging and task calls
    assert logger_info.call_args_list == [
        call(f"Starting build_subscription for bag {model.bag.id}"),
        call(f"Subscription was created with id 1"),
    ]
    assert logger_error.call_args_list == []
    assert build_scheduler.call_args_list == [call(1)]
