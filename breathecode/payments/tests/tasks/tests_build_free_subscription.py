"""
Test /answer
"""

import logging
import random
from unittest.mock import MagicMock, call, patch

import pytest
from django.utils import timezone

import breathecode.activity.tasks as activity_tasks
from breathecode.payments import tasks
from breathecode.payments.actions import calculate_relative_delta

from ...tasks import build_free_subscription
from ..mixins import PaymentsTestCase

UTC_NOW = timezone.now()


def subscription_item(data={}):
    return {
        "id": 1,
        "academy_id": 1,
        "is_refundable": True,
        "paid_at": UTC_NOW,
        "pay_every": 1,
        "pay_every_unit": "MONTH",
        "selected_cohort_set_id": None,
        "selected_event_type_set_id": None,
        "selected_mentorship_service_set_id": None,
        "status": "ACTIVE",
        "status_message": None,
        "user_id": 1,
        "valid_until": UTC_NOW,
        "externally_managed": False,
        **data,
    }


@pytest.fixture(autouse=True)
def setup(monkeypatch):
    monkeypatch.setattr(activity_tasks.add_activity, "delay", MagicMock())
    yield


# FIXME: create_v2 fail in this test file
class PaymentsTestSuite(PaymentsTestCase):
    """
    🔽🔽🔽 Bag not found
    """

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    def test_bag_not_found(self):
        build_free_subscription.delay(1, 1)

        self.assertEqual(self.bc.database.list_of("admissions.Cohort"), [])

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting build_free_subscription for bag 1"),
                # retry
                call("Starting build_free_subscription for bag 1"),
            ],
        )
        self.assertEqual(logging.Logger.error.call_args_list, [call("Bag with id 1 not found", exc_info=True)])

        self.assertEqual(self.bc.database.list_of("payments.Bag"), [])
        self.assertEqual(self.bc.database.list_of("payments.Invoice"), [])
        self.assertEqual(self.bc.database.list_of("payments.Subscription"), [])
        self.bc.check.calls(activity_tasks.add_activity.delay.call_args_list, [])

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

        build_free_subscription.delay(1, 1)

        self.assertEqual(self.bc.database.list_of("admissions.Cohort"), [])

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting build_free_subscription for bag 1"),
                # retry
                call("Starting build_free_subscription for bag 1"),
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

    """
    🔽🔽🔽 With Bag and Invoice
    """

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch.object(timezone, "now", MagicMock(return_value=UTC_NOW))
    @patch("breathecode.payments.tasks.build_service_stock_scheduler_from_subscription.delay", MagicMock())
    def test_without_plan(self):
        bag = {
            "status": "PAID",
            "was_delivered": False,
            "chosen_period": random.choice(["MONTH", "QUARTER", "HALF", "YEAR"]),
        }
        invoice = {"status": "FULFILLED"}

        model = self.bc.database.create(bag=bag, invoice=invoice)

        # remove prints from mixer
        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        build_free_subscription.delay(1, 1)

        self.assertEqual(self.bc.database.list_of("admissions.Cohort"), [])

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting build_free_subscription for bag 1"),
            ],
        )
        self.assertEqual(
            logging.Logger.error.call_args_list,
            [
                call("Not have plans to associated to this free subscription in the bag 1", exc_info=True),
            ],
        )

        self.assertEqual(
            self.bc.database.list_of("payments.Bag"),
            [
                {
                    **self.bc.format.to_dict(model.bag),
                    "was_delivered": False,
                },
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("payments.Invoice"),
            [
                self.bc.format.to_dict(model.invoice),
            ],
        )
        self.assertEqual(self.bc.database.list_of("payments.Subscription"), [])
        self.assertEqual(tasks.build_service_stock_scheduler_from_subscription.delay.call_args_list, [])
        self.bc.check.calls(
            activity_tasks.add_activity.delay.call_args_list,
            [
                call(1, "bag_created", related_type="payments.Bag", related_id=1),
            ],
        )

    """
    🔽🔽🔽 With Bag, Invoice and Plan
    """

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch.object(timezone, "now", MagicMock(return_value=UTC_NOW))
    @patch("breathecode.payments.tasks.build_service_stock_scheduler_from_subscription.delay", MagicMock())
    def test_subscription_was_created__is_free_trial(self):
        bag = {
            "status": "PAID",
            "was_delivered": False,
            "chosen_period": "NO_SET",
        }
        invoice = {"status": "FULFILLED"}

        plans = [
            {
                "is_renewable": False,
                "trial_duration": random.randint(1, 100),
                "trial_duration_unit": random.choice(["DAY", "WEEK", "MONTH", "YEAR"]),
            }
            for _ in range(2)
        ]

        model = self.bc.database.create(bag=bag, invoice=invoice, plan=plans)

        # remove prints from mixer
        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        build_free_subscription.delay(1, 1)

        self.assertEqual(self.bc.database.list_of("admissions.Cohort"), [])

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting build_free_subscription for bag 1"),
                call("Free subscription was created with id 1 for plan 1"),
                call("Free subscription was created with id 2 for plan 2"),
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

        db = []
        for plan in model.plan:
            unit = plan.trial_duration
            unit_type = plan.trial_duration_unit
            db.append(
                subscription_item(
                    {
                        "conversion_info": None,
                        "id": plan.id,
                        "status": "FREE_TRIAL",
                        "paid_at": model.invoice.paid_at,
                        "next_payment_at": model.invoice.paid_at + calculate_relative_delta(unit, unit_type),
                        "valid_until": model.invoice.paid_at + calculate_relative_delta(unit, unit_type),
                    }
                )
            )

        self.assertEqual(self.bc.database.list_of("payments.Subscription"), db)
        self.assertEqual(
            tasks.build_service_stock_scheduler_from_subscription.delay.call_args_list,
            [
                call(1),
                call(2),
            ],
        )
        self.bc.check.calls(
            activity_tasks.add_activity.delay.call_args_list,
            [
                call(1, "bag_created", related_type="payments.Bag", related_id=1),
            ],
        )

    """
    🔽🔽🔽 With Bag, Invoice with amount and Plan
    """

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch.object(timezone, "now", MagicMock(return_value=UTC_NOW))
    @patch("breathecode.payments.tasks.build_service_stock_scheduler_from_subscription.delay", MagicMock())
    def test_invoice_with_amount(self):
        bag = {
            "status": "PAID",
            "was_delivered": False,
            "chosen_period": random.choice(["MONTH", "QUARTER", "HALF", "YEAR"]),
        }
        invoice = {"status": "FULFILLED", "amount": (random.random() * 99.99) + 0.01}

        plans = [
            {
                "is_renewable": False,
                "trial_duration": random.randint(1, 100),
                "trial_duration_unit": random.choice(["DAY", "WEEK", "MONTH", "YEAR"]),
            }
            for _ in range(2)
        ]

        model = self.bc.database.create(bag=bag, invoice=invoice, plan=plans)

        # remove prints from mixer
        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        build_free_subscription.delay(1, 1)

        self.assertEqual(self.bc.database.list_of("admissions.Cohort"), [])

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting build_free_subscription for bag 1"),
            ],
        )

        self.assertEqual(
            logging.Logger.error.call_args_list,
            [
                call("The invoice with id 1 is invalid for a free subscription", exc_info=True),
            ],
        )

        self.assertEqual(
            self.bc.database.list_of("payments.Bag"),
            [
                {
                    **self.bc.format.to_dict(model.bag),
                    "was_delivered": False,
                },
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("payments.Invoice"),
            [
                self.bc.format.to_dict(model.invoice),
            ],
        )

        self.assertEqual(self.bc.database.list_of("payments.Subscription"), [])
        self.assertEqual(tasks.build_service_stock_scheduler_from_subscription.delay.call_args_list, [])
        self.bc.check.calls(
            activity_tasks.add_activity.delay.call_args_list,
            [
                call(1, "bag_created", related_type="payments.Bag", related_id=1),
            ],
        )

    """
    🔽🔽🔽 With Bag with Cohort, Invoice and Plan
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

        plans = [
            {
                "is_renewable": False,
                "trial_duration": random.randint(1, 100),
                "trial_duration_unit": random.choice(["DAY", "WEEK", "MONTH", "YEAR"]),
            }
            for _ in range(2)
        ]
        academy = {"available_as_saas": True}

        model = self.bc.database.create(bag=bag, invoice=invoice, plan=plans, cohort=1, cohort_set=1, academy=academy)

        # remove prints from mixer
        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        build_free_subscription.delay(1, 1)

        self.assertEqual(
            self.bc.database.list_of("admissions.Cohort"),
            [
                self.bc.format.to_dict(model.cohort),
            ],
        )

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting build_free_subscription for bag 1"),
                call("Free subscription was created with id 1 for plan 1"),
                call("Free subscription was created with id 2 for plan 2"),
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

        db = []
        for plan in model.plan:
            unit = plan.trial_duration
            unit_type = plan.trial_duration_unit
            db.append(
                subscription_item(
                    {
                        "conversion_info": None,
                        "id": plan.id,
                        "selected_cohort_set_id": 1,
                        "status": "FREE_TRIAL",
                        "paid_at": model.invoice.paid_at,
                        "next_payment_at": model.invoice.paid_at + calculate_relative_delta(unit, unit_type),
                        "valid_until": model.invoice.paid_at + calculate_relative_delta(unit, unit_type),
                    }
                )
            )

        self.assertEqual(self.bc.database.list_of("payments.Subscription"), db)
        self.assertEqual(
            tasks.build_service_stock_scheduler_from_subscription.delay.call_args_list,
            [
                call(1),
                call(2),
            ],
        )
        self.bc.check.calls(
            activity_tasks.add_activity.delay.call_args_list,
            [
                call(1, "bag_created", related_type="payments.Bag", related_id=1),
            ],
        )

    """
    🔽🔽🔽 With Bag with EventTypeSet, Invoice and Plan
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

        plans = [
            {
                "is_renewable": False,
                "trial_duration": random.randint(1, 100),
                "trial_duration_unit": random.choice(["DAY", "WEEK", "MONTH", "YEAR"]),
            }
            for _ in range(2)
        ]

        model = self.bc.database.create(bag=bag, invoice=invoice, plan=plans, event_type_set=1)

        # remove prints from mixer
        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        build_free_subscription.delay(1, 1)

        self.assertEqual(self.bc.database.list_of("admissions.Cohort"), [])

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting build_free_subscription for bag 1"),
                call("Free subscription was created with id 1 for plan 1"),
                call("Free subscription was created with id 2 for plan 2"),
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

        db = []
        for plan in model.plan:
            unit = plan.trial_duration
            unit_type = plan.trial_duration_unit
            db.append(
                subscription_item(
                    {
                        "conversion_info": None,
                        "id": plan.id,
                        "selected_event_type_set_id": 1,
                        "status": "FREE_TRIAL",
                        "paid_at": model.invoice.paid_at,
                        "next_payment_at": model.invoice.paid_at + calculate_relative_delta(unit, unit_type),
                        "valid_until": model.invoice.paid_at + calculate_relative_delta(unit, unit_type),
                    }
                )
            )

        self.assertEqual(self.bc.database.list_of("payments.Subscription"), db)
        self.assertEqual(
            tasks.build_service_stock_scheduler_from_subscription.delay.call_args_list,
            [
                call(1),
                call(2),
            ],
        )
        self.bc.check.calls(
            activity_tasks.add_activity.delay.call_args_list,
            [
                call(1, "bag_created", related_type="payments.Bag", related_id=1),
            ],
        )

    """
    🔽🔽🔽 With Bag with MentorshipServiceSet, Invoice and Plan
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

        plans = [
            {
                "is_renewable": False,
                "trial_duration": random.randint(1, 100),
                "trial_duration_unit": random.choice(["DAY", "WEEK", "MONTH", "YEAR"]),
            }
            for _ in range(2)
        ]

        model = self.bc.database.create(bag=bag, invoice=invoice, plan=plans, mentorship_service_set=1)

        # remove prints from mixer
        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        build_free_subscription.delay(1, 1)

        self.assertEqual(self.bc.database.list_of("admissions.Cohort"), [])

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting build_free_subscription for bag 1"),
                call("Free subscription was created with id 1 for plan 1"),
                call("Free subscription was created with id 2 for plan 2"),
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

        db = []
        for plan in model.plan:
            unit = plan.trial_duration
            unit_type = plan.trial_duration_unit
            db.append(
                subscription_item(
                    {
                        "conversion_info": None,
                        "id": plan.id,
                        "selected_mentorship_service_set_id": 1,
                        "status": "FREE_TRIAL",
                        "paid_at": model.invoice.paid_at,
                        "next_payment_at": model.invoice.paid_at + calculate_relative_delta(unit, unit_type),
                        "valid_until": model.invoice.paid_at + calculate_relative_delta(unit, unit_type),
                    }
                )
            )

        self.assertEqual(self.bc.database.list_of("payments.Subscription"), db)
        self.assertEqual(
            tasks.build_service_stock_scheduler_from_subscription.delay.call_args_list,
            [
                call(1),
                call(2),
            ],
        )
        self.bc.check.calls(
            activity_tasks.add_activity.delay.call_args_list,
            [
                call(1, "bag_created", related_type="payments.Bag", related_id=1),
            ],
        )

    """
    🔽🔽🔽 With Bag, Invoice and Plan with is_renewable=False
    """

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch.object(timezone, "now", MagicMock(return_value=UTC_NOW))
    @patch("breathecode.payments.tasks.build_service_stock_scheduler_from_subscription.delay", MagicMock())
    def test_subscription_was_created__is_free__is_not_renewable(self):
        bag = {
            "status": "PAID",
            "was_delivered": False,
            "chosen_period": "NO_SET",
        }
        invoice = {"status": "FULFILLED"}

        plans = [
            {
                "is_renewable": False,
                "trial_duration": 0,
                "trial_duration_unit": random.choice(["DAY", "WEEK", "MONTH", "YEAR"]),
                "time_of_life": random.randint(1, 100),
                "time_of_life_unit": random.choice(["DAY", "WEEK", "MONTH", "YEAR"]),
            }
            for _ in range(2)
        ]

        model = self.bc.database.create(bag=bag, invoice=invoice, plan=plans)

        # remove prints from mixer
        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        build_free_subscription.delay(1, 1)

        self.assertEqual(self.bc.database.list_of("admissions.Cohort"), [])

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting build_free_subscription for bag 1"),
                call("Free subscription was created with id 1 for plan 1"),
                call("Free subscription was created with id 2 for plan 2"),
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

        db = []
        for plan in model.plan:
            unit = plan.time_of_life
            unit_type = plan.time_of_life_unit
            db.append(
                subscription_item(
                    {
                        "conversion_info": None,
                        "id": plan.id,
                        "status": "ACTIVE",
                        "paid_at": model.invoice.paid_at,
                        "next_payment_at": model.invoice.paid_at + calculate_relative_delta(unit, unit_type),
                        "valid_until": model.invoice.paid_at + calculate_relative_delta(unit, unit_type),
                    }
                )
            )

        self.assertEqual(self.bc.database.list_of("payments.Subscription"), db)
        self.assertEqual(
            tasks.build_service_stock_scheduler_from_subscription.delay.call_args_list,
            [
                call(1),
                call(2),
            ],
        )
        self.bc.check.calls(
            activity_tasks.add_activity.delay.call_args_list,
            [
                call(1, "bag_created", related_type="payments.Bag", related_id=1),
            ],
        )

    """
    🔽🔽🔽 With Bag, Invoice and Plan with is_renewable=True
    """

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch.object(timezone, "now", MagicMock(return_value=UTC_NOW))
    @patch("breathecode.payments.tasks.build_service_stock_scheduler_from_subscription.delay", MagicMock())
    def test_subscription_was_created__is_free__is_renewable(self):
        bag = {
            "status": "PAID",
            "was_delivered": False,
            "chosen_period": "NO_SET",
        }
        invoice = {"status": "FULFILLED"}

        plans = [
            {
                "is_renewable": True,
                "trial_duration": 0,
                "trial_duration_unit": random.choice(["DAY", "WEEK", "MONTH", "YEAR"]),
                "time_of_life": random.randint(1, 100),
                "time_of_life_unit": random.choice(["DAY", "WEEK", "MONTH", "YEAR"]),
            }
            for _ in range(2)
        ]

        model = self.bc.database.create(bag=bag, invoice=invoice, plan=plans)

        # remove prints from mixer
        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        build_free_subscription.delay(1, 1)

        self.assertEqual(self.bc.database.list_of("admissions.Cohort"), [])

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting build_free_subscription for bag 1"),
                call("Free subscription was created with id 1 for plan 1"),
                call("Free subscription was created with id 2 for plan 2"),
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

        db = []
        for plan in model.plan:
            unit = plan.time_of_life
            unit_type = plan.time_of_life_unit
            db.append(
                subscription_item(
                    {
                        "conversion_info": None,
                        "id": plan.id,
                        "status": "ACTIVE",
                        "paid_at": model.invoice.paid_at,
                        "next_payment_at": model.invoice.paid_at + calculate_relative_delta(unit, unit_type),
                        "valid_until": None,
                    }
                )
            )

        self.assertEqual(self.bc.database.list_of("payments.Subscription"), db)
        self.assertEqual(
            tasks.build_service_stock_scheduler_from_subscription.delay.call_args_list,
            [
                call(1),
                call(2),
            ],
        )
        self.bc.check.calls(
            activity_tasks.add_activity.delay.call_args_list,
            [
                call(1, "bag_created", related_type="payments.Bag", related_id=1),
            ],
        )

    """
    🔽🔽🔽 With Bag, Invoice and Plan with is_renewable=True
    """

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch.object(timezone, "now", MagicMock(return_value=UTC_NOW))
    @patch("breathecode.payments.tasks.build_service_stock_scheduler_from_subscription.delay", MagicMock())
    def test_subscription_was_created__is_free__is_renewable_with_conversion_info(self):
        bag = {
            "status": "PAID",
            "was_delivered": False,
            "chosen_period": "NO_SET",
        }
        invoice = {"status": "FULFILLED"}

        plans = [
            {
                "is_renewable": True,
                "trial_duration": 0,
                "trial_duration_unit": random.choice(["DAY", "WEEK", "MONTH", "YEAR"]),
                "time_of_life": random.randint(1, 100),
                "time_of_life_unit": random.choice(["DAY", "WEEK", "MONTH", "YEAR"]),
            }
            for _ in range(2)
        ]

        model = self.bc.database.create(bag=bag, invoice=invoice, plan=plans)

        # remove prints from mixer
        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        build_free_subscription.delay(1, 1, conversion_info='{"landing_url": "/"}')

        self.assertEqual(self.bc.database.list_of("admissions.Cohort"), [])

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting build_free_subscription for bag 1"),
                call("Free subscription was created with id 1 for plan 1"),
                call("Free subscription was created with id 2 for plan 2"),
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

        db = []
        for plan in model.plan:
            unit = plan.time_of_life
            unit_type = plan.time_of_life_unit
            db.append(
                subscription_item(
                    {
                        "conversion_info": {"landing_url": "/"},
                        "id": plan.id,
                        "status": "ACTIVE",
                        "paid_at": model.invoice.paid_at,
                        "next_payment_at": model.invoice.paid_at + calculate_relative_delta(unit, unit_type),
                        "valid_until": None,
                    }
                )
            )

        self.assertEqual(self.bc.database.list_of("payments.Subscription"), db)
        self.assertEqual(
            tasks.build_service_stock_scheduler_from_subscription.delay.call_args_list,
            [
                call(1),
                call(2),
            ],
        )
        self.bc.check.calls(
            activity_tasks.add_activity.delay.call_args_list,
            [
                call(1, "bag_created", related_type="payments.Bag", related_id=1),
            ],
        )
