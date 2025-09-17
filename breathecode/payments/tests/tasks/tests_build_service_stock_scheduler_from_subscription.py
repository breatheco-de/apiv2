"""
Test /answer
"""

import logging
import pytest
from unittest.mock import MagicMock, call, patch

from django.utils import timezone
from breathecode.payments import tasks
from breathecode.payments.actions import calculate_relative_delta
from breathecode.payments.models import (
    SubscriptionBillingTeam,
    SubscriptionSeat,
    SubscriptionServiceItem,
    PlanServiceItem,
    ServiceStockScheduler,
)

from ...tasks import build_service_stock_scheduler_from_subscription

from ..mixins import PaymentsTestCase
from dateutil.relativedelta import relativedelta

UTC_NOW = timezone.now()


@pytest.fixture(autouse=True)
def mock_renew_subscription_consumables(monkeypatch: pytest.MonkeyPatch):
    # tasks.renew_subscription_consumables.delay
    monkeypatch.setattr(
        "breathecode.payments.tasks.build_service_stock_scheduler_from_subscription.delay",
        MagicMock(wraps=tasks.build_service_stock_scheduler_from_subscription.delay),
    )


def service_stock_scheduler_item(data={}):
    return {
        "id": 1,
        "plan_handler_id": None,
        "subscription_handler_id": None,
        "subscription_seat_id": None,
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
        self.assertEqual(tasks.renew_subscription_consumables.delay.call_args_list, [call(1, seat_id=None)])
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
        self.assertEqual(tasks.renew_subscription_consumables.delay.call_args_list, [call(1, seat_id=None)])
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
        self.assertEqual(tasks.renew_subscription_consumables.delay.call_args_list, [call(1, seat_id=None)])
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
        self.assertEqual(tasks.renew_subscription_consumables.delay.call_args_list, [call(1, seat_id=None)])
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

    """
    🔽🔽🔽 Team scenarios
    - When a subscription has seats and a service_item has is_team_allowed=False,
      we must build owner-level schedulers only and renew owner; per-seat builds are scheduled for team-allowed items only.
    - When is_team_allowed=True, owner-level schedulers should NOT be created, only per-seat builds should be scheduled.
"""


@patch("logging.Logger.info", MagicMock())
@patch("logging.Logger.error", MagicMock())
@patch("breathecode.payments.tasks.renew_subscription_consumables.delay", MagicMock())
# do not patch the task under test, we need it to execute
@patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
def test_build_scheduler_for_owner_with_non_team_item(database):
    # seat service item
    seat_model = database.create(service={"type": "SEAT"}, service_item={"how_many": 0})

    subscription = {
        "next_payment_at": UTC_NOW + relativedelta(months=1),
        "valid_until": UTC_NOW + relativedelta(months=2),
        "seat_service_item": seat_model.service_item,
    }

    # Non-team service item linked to subscription
    non_team_service = database.create(service=1, service_item={"is_team_allowed": False})

    # Create the subscription
    model = database.create(
        subscription=subscription,
        subscription_service_item={"service_item": non_team_service.service_item},
        city=1,
        country=1,
    )

    # Ensure team and a seat exists
    team = SubscriptionBillingTeam.objects.create(subscription=model.subscription, name=f"Team {model.subscription.id}")
    SubscriptionSeat.objects.create(
        billing_team=team, user=model.user, email=model.user.email, is_active=True, seat_multiplier=1
    )

    # Clean logger calls
    logging.Logger.info.call_args_list = []
    logging.Logger.error.call_args_list = []

    # Act
    build_service_stock_scheduler_from_subscription.delay(1)

    # Assert: owner renew called (owner-level path does not pass seat_id)
    assert tasks.renew_subscription_consumables.delay.call_args_list == [call(1, seat_id=None)]

    # We don't assert nested scheduling calls here to allow the task to run

    # Owner-level scheduler created for non-team service item
    schedulers = database.list_of("payments.ServiceStockScheduler")
    assert len(schedulers) == 1
    assert schedulers[0]["subscription_handler_id"] == 1
    assert schedulers[0]["plan_handler_id"] is None
    assert schedulers[0]["subscription_seat_id"] is None


@pytest.mark.django_db
def test_build_scheduler_for_seat_with_non_team_subscription_item(database, monkeypatch: pytest.MonkeyPatch):
    # Patch renew to capture calls
    monkeypatch.setattr("breathecode.payments.tasks.renew_subscription_consumables.delay", MagicMock())
    monkeypatch.setattr("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))

    # Seat configuration on subscription
    seat_model = database.create(service={"type": "SEAT"}, service_item={"how_many": 0})
    subscription = {
        "next_payment_at": UTC_NOW + relativedelta(months=1),
        "valid_until": UTC_NOW + relativedelta(months=2),
        "seat_service_item": seat_model.service_item,
    }

    # Non-team subscription item
    non_team_service = database.create(service=1, service_item={"is_team_allowed": False})

    model = database.create(
        subscription=subscription,
        subscription_service_item={"service_item": non_team_service.service_item},
        academy={"available_as_saas": True},
        country=1,
        city=1,
    )

    # Team and seat
    team = SubscriptionBillingTeam.objects.create(subscription=model.subscription, name=f"Team {model.subscription.id}")
    seat_owner = SubscriptionSeat.objects.create(
        billing_team=team, user=model.user, email=model.user.email, is_active=True, seat_multiplier=1
    )

    # Act: build only for this seat
    tasks.build_service_stock_scheduler_from_subscription.delay(model.subscription.id, seat_id=seat_owner.id)

    # Assert: renew called with seat_id; no schedulers were created for non-team items
    assert tasks.renew_subscription_consumables.delay.call_args_list == [
        call(model.subscription.id, seat_id=seat_owner.id)
    ]
    assert database.list_of("payments.ServiceStockScheduler") == []


@pytest.mark.django_db
def test_build_scheduler_for_team_and_non_team_items(database, monkeypatch: pytest.MonkeyPatch):
    # Capture renew calls
    monkeypatch.setattr("breathecode.payments.tasks.renew_consumables.delay", MagicMock())
    monkeypatch.setattr("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))

    # Subscription with seats
    seat_model = database.create(service={"type": "SEAT"}, service_item={"how_many": 0})
    subscription = {
        "next_payment_at": UTC_NOW + relativedelta(months=1),
        "valid_until": UTC_NOW + relativedelta(months=2),
        "seat_service_item": seat_model.service_item,
    }

    model = database.create(
        subscription=subscription,
        service=2,
        service_item=[{"service_id": 1, "is_team_allowed": False}, {"service_id": 2, "is_team_allowed": True}],
        subscription_service_item=2,
        academy={"available_as_saas": True},
        country=1,
        city=1,
    )

    # Team and seat
    team = SubscriptionBillingTeam.objects.create(subscription=model.subscription, name=f"Team {model.subscription.id}")
    seat_owner = SubscriptionSeat.objects.create(
        billing_team=team, user=model.user, email=model.user.email, is_active=True, seat_multiplier=1
    )

    # Act: build schedulers for the subscription
    tasks.build_service_stock_scheduler_from_subscription.delay(model.subscription.id)

    # Assert: only owner-level scheduler is created for the non-team item
    schedulers = database.list_of("payments.ServiceStockScheduler")
    assert len(schedulers) == 1

    assert schedulers[0]["subscription_handler_id"] is not None
    assert schedulers[0]["subscription_seat_id"] is None


@pytest.mark.django_db
def test_build_scheduler_for_seat_with_non_team_plan_item(database, monkeypatch: pytest.MonkeyPatch):
    # Patch renew to capture calls
    monkeypatch.setattr("breathecode.payments.tasks.renew_subscription_consumables.delay", MagicMock())
    monkeypatch.setattr("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))

    # Seat configuration on subscription
    seat_model = database.create(service={"type": "SEAT"}, service_item={"how_many": 0})
    subscription = {
        "next_payment_at": UTC_NOW + relativedelta(months=1),
        "valid_until": UTC_NOW + relativedelta(months=2),
        "seat_service_item": seat_model.service_item,
    }

    # Non-team plan item
    non_team_service = database.create(service=1, service_item={"is_team_allowed": False})

    model = database.create(
        subscription=subscription,
        plan={"is_renewable": False},
        plan_service_item={"service_item": non_team_service.service_item},
        academy={"available_as_saas": True},
        country=1,
        city=1,
    )

    # Team and seat
    team = SubscriptionBillingTeam.objects.create(subscription=model.subscription, name=f"Team {model.subscription.id}")
    seat_owner = SubscriptionSeat.objects.create(
        billing_team=team, user=model.user, email=model.user.email, is_active=True, seat_multiplier=1
    )

    # Act: build only for this seat
    tasks.build_service_stock_scheduler_from_subscription.delay(model.subscription.id, seat_id=seat_owner.id)

    # Assert: renew called with seat_id; no schedulers were created for non-team items
    assert tasks.renew_subscription_consumables.delay.call_args_list == [
        call(model.subscription.id, seat_id=seat_owner.id)
    ]
    assert database.list_of("payments.ServiceStockScheduler") == []
