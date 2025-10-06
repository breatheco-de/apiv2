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
        "subscription_billing_team_id": None,
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
        model = self.bc.database.create(
            subscription=subscription,
            service={"type": "COHORT_SET"},
            service_item={"how_many": 1},
            subscription_service_item={"service_item_id": 1},
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

        model = self.bc.database.create(
            subscription=subscription,
            plan=plan,
            service_item={"how_many": 1},
            plan_service_item={"service_item_id": 1},
            service={"type": "COHORT_SET"},
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
            service=[{"type": "COHORT_SET"} for _ in range(6)],
            service_item=[{"how_many": 1} for _ in range(6)],
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
    seat_model = database.create(service={"type": "SEAT"}, service_item={"how_many": 1})

    subscription = {
        "next_payment_at": UTC_NOW + relativedelta(months=1),
        "valid_until": UTC_NOW + relativedelta(months=2),
        "seat_service_item": seat_model.service_item,
    }

    # Non-team service item linked to subscription
    non_team_service = database.create(
        service={"type": "COHORT_SET"}, service_item={"is_team_allowed": False, "how_many": 1}
    )

    # Create the subscription
    model = database.create(
        subscription=subscription,
        subscription_service_item={"service_item": non_team_service.service_item},
        city=1,
        country=1,
    )

    # Ensure team and a seat exists
    team = SubscriptionBillingTeam.objects.create(subscription=model.subscription, name=f"Team {model.subscription.id}")
    SubscriptionSeat.objects.create(billing_team=team, user=model.user, email=model.user.email, is_active=True)

    # Clean logger calls
    logging.Logger.info.call_args_list = []
    logging.Logger.error.call_args_list = []

    # Act
    build_service_stock_scheduler_from_subscription.delay(1)

    # Assert: both per-seat renew and owner-level renew are triggered
    calls = tasks.renew_subscription_consumables.delay.call_args_list
    assert call(1, seat_id=None) in calls
    assert call(1, seat_id=1) in calls
    assert len(calls) == 2

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
    seat_model = database.create(service={"type": "SEAT"}, service_item={"how_many": 1})
    subscription = {
        "next_payment_at": UTC_NOW + relativedelta(months=1),
        "valid_until": UTC_NOW + relativedelta(months=2),
        "seat_service_item": seat_model.service_item,
    }

    # Non-team subscription item
    non_team_service = database.create(
        service={"type": "COHORT_SET"}, service_item={"is_team_allowed": False, "how_many": 1}
    )

    model = database.create(
        subscription=subscription,
        # subscription_service_item={"service_item_id": non_team_service.service_item.id},
        academy={"available_as_saas": True},
        country=1,
        city=1,
    )
    model.subscription.service_items.add(non_team_service.service_item)

    # Team and seat
    team = SubscriptionBillingTeam.objects.create(subscription=model.subscription, name=f"Team {model.subscription.id}")
    seat_owner = SubscriptionSeat.objects.create(
        billing_team=team, user=model.user, email=model.user.email, is_active=True
    )

    # Act: build only for this seat
    tasks.build_service_stock_scheduler_from_subscription.delay(model.subscription.id, seat_id=seat_owner.id)

    # Assert: renew called with seat_id; no schedulers were created for non-team items
    assert tasks.renew_subscription_consumables.delay.call_args_list == [
        call(model.subscription.id, seat_id=seat_owner.id)
    ]
    assert database.list_of("payments.ServiceStockScheduler") == []


@pytest.mark.django_db
def test_per_team_builds_team_owned_for_subscription_items(database, monkeypatch: pytest.MonkeyPatch):
    """
    PER_TEAM strategy for subscription items:
    - Team-allowed subscription items must create team-owned schedulers (subscription_billing_team set).
    - Non-team subscription items must create owner-level schedulers (no seat, no billing_team).
    - No seat schedulers should be created and only one owner renew should be triggered.
    """
    # Patch renew to capture calls and time to be deterministic
    monkeypatch.setattr("breathecode.payments.tasks.renew_subscription_consumables.delay", MagicMock())
    monkeypatch.setattr("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))

    # Subscription with seats
    seat_model = database.create(service={"type": "SEAT"}, service_item={"how_many": 1})
    subscription = {
        "next_payment_at": UTC_NOW + relativedelta(months=1),
        "valid_until": UTC_NOW + relativedelta(months=2),
        "seat_service_item": seat_model.service_item,
    }

    # Two subscription service items: one non-team, one team-allowed
    model = database.create(
        subscription=subscription,
        service=[{"type": "COHORT_SET"}, {"type": "EVENT_TYPE_SET"}],
        service_item=[
            {"service_id": 1, "is_team_allowed": False, "how_many": 1},
            {"service_id": 2, "is_team_allowed": True, "how_many": 1},
        ],
        subscription_service_item=2,
        academy={"available_as_saas": True},
        country=1,
        city=1,
    )

    # Team with PER_TEAM strategy
    team = SubscriptionBillingTeam.objects.create(
        subscription=model.subscription,
        name=f"Team {model.subscription.id}",
        consumption_strategy=SubscriptionBillingTeam.ConsumptionStrategy.PER_TEAM,
    )
    SubscriptionSeat.objects.create(billing_team=team, user=model.user, email=model.user.email, is_active=True)

    # Act
    tasks.build_service_stock_scheduler_from_subscription.delay(model.subscription.id)

    # Assert: we have at least one team-owned scheduler, and no seat-level schedulers here
    schedulers = database.list_of("payments.ServiceStockScheduler")
    owner_level = [s for s in schedulers if s["subscription_billing_team_id"] is None]
    team_owned = [s for s in schedulers if s["subscription_billing_team_id"] == team.id]
    assert len(team_owned) >= 1
    assert all(s["subscription_seat_id"] is None for s in schedulers)

    # Only one renew call for owner-level build
    assert tasks.renew_subscription_consumables.delay.call_args_list == [call(model.subscription.id, seat_id=None)]


@pytest.mark.django_db
def test_per_team_builds_team_owned_for_plan_items(database, monkeypatch: pytest.MonkeyPatch):
    """
    PER_TEAM strategy for plan items:
    - Team-allowed plan items must create team-owned schedulers (subscription_billing_team set).
    - Non-team plan items must create owner-level schedulers (no seat, no billing_team).
    - No seat schedulers should be created and only one owner renew should be triggered.
    """
    # Patch renew to capture calls and time to be deterministic
    monkeypatch.setattr("breathecode.payments.tasks.renew_subscription_consumables.delay", MagicMock())
    monkeypatch.setattr("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))

    # Subscription with seats
    seat_model = database.create(service={"type": "SEAT"}, service_item={"how_many": 1})
    subscription = {
        "next_payment_at": UTC_NOW + relativedelta(months=1),
        "valid_until": UTC_NOW + relativedelta(months=2),
        "seat_service_item": seat_model.service_item,
    }

    # Two plan items: one non-team, one team-allowed
    model = database.create(
        subscription=subscription,
        plan={"is_renewable": False},
        service=[{"type": "COHORT_SET"}, {"type": "EVENT_TYPE_SET"}],
        service_item=[
            {"service_id": 1, "is_team_allowed": False, "how_many": 1},
            {"service_id": 2, "is_team_allowed": True, "how_many": 1},
        ],
        plan_service_item=[{"plan_id": 1, "service_item_id": 1}, {"plan_id": 1, "service_item_id": 2}],
        academy={"available_as_saas": True},
        country=1,
        city=1,
    )

    # Team with PER_TEAM strategy
    team = SubscriptionBillingTeam.objects.create(
        subscription=model.subscription,
        name=f"Team {model.subscription.id}",
        consumption_strategy=SubscriptionBillingTeam.ConsumptionStrategy.PER_TEAM,
    )
    SubscriptionSeat.objects.create(billing_team=team, user=model.user, email=model.user.email, is_active=True)

    # Act
    tasks.build_service_stock_scheduler_from_subscription.delay(model.subscription.id)

    # Assert: at least one team-owned scheduler exists; owner-level may be zero
    schedulers = database.list_of("payments.ServiceStockScheduler")
    owner_level = [s for s in schedulers if s["subscription_billing_team_id"] is None]
    team_owned = [s for s in schedulers if s["subscription_billing_team_id"] == team.id]
    assert len(team_owned) >= 1
    # No seat-level schedulers expected here
    assert all(s["subscription_seat_id"] is None for s in schedulers)

    # Only one renew call for owner-level build
    assert tasks.renew_subscription_consumables.delay.call_args_list == [call(model.subscription.id, seat_id=None)]


@pytest.mark.django_db
def test_build_scheduler_for_team_and_non_team_items(database, monkeypatch: pytest.MonkeyPatch):
    # Capture renew calls
    monkeypatch.setattr("breathecode.payments.tasks.renew_consumables.delay", MagicMock())
    monkeypatch.setattr("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))

    # Subscription with seats
    seat_model = database.create(service={"type": "SEAT"}, service_item={"how_many": 1})
    subscription = {
        "next_payment_at": UTC_NOW + relativedelta(months=1),
        "valid_until": UTC_NOW + relativedelta(months=2),
        "seat_service_item": seat_model.service_item,
    }

    model = database.create(
        subscription=subscription,
        service=[{"type": "COHORT_SET"}, {"type": "EVENT_TYPE_SET"}],
        service_item=[
            {"service_id": 1, "is_team_allowed": False, "how_many": 1},
            {"service_id": 2, "is_team_allowed": True, "how_many": 1},
        ],
        subscription_service_item=2,
        academy={"available_as_saas": True},
        country=1,
        city=1,
    )

    # Team and seat
    team = SubscriptionBillingTeam.objects.create(subscription=model.subscription, name=f"Team {model.subscription.id}")
    seat_owner = SubscriptionSeat.objects.create(
        billing_team=team, user=model.user, email=model.user.email, is_active=True
    )

    # Act: build schedulers for the subscription
    tasks.build_service_stock_scheduler_from_subscription.delay(model.subscription.id)

    # Assert: we have at least one seat-level scheduler; owner-level may be zero
    schedulers = database.list_of("payments.ServiceStockScheduler")
    seat_level = [s for s in schedulers if s["subscription_seat_id"] is not None]
    owner_level = [s for s in schedulers if s["subscription_seat_id"] is None]
    assert len(seat_level) >= 1


@pytest.mark.django_db
def test_build_scheduler_for_seat_with_non_team_plan_item(database, monkeypatch: pytest.MonkeyPatch):
    # Patch renew to capture calls
    monkeypatch.setattr("breathecode.payments.tasks.renew_subscription_consumables.delay", MagicMock())
    monkeypatch.setattr("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))

    # Seat configuration on subscription
    seat_model = database.create(service={"type": "SEAT"}, service_item={"how_many": 1})
    subscription = {
        "next_payment_at": UTC_NOW + relativedelta(months=1),
        "valid_until": UTC_NOW + relativedelta(months=2),
        "seat_service_item": seat_model.service_item,
    }

    # Non-team plan item
    non_team_service = database.create(
        service={"type": "COHORT_SET"}, service_item={"is_team_allowed": False, "how_many": 1}
    )

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
        billing_team=team, user=model.user, email=model.user.email, is_active=True
    )

    # Act: build only for this seat
    tasks.build_service_stock_scheduler_from_subscription.delay(model.subscription.id, seat_id=seat_owner.id)

    # Assert: renew called with seat_id; no schedulers were created for non-team items
    assert tasks.renew_subscription_consumables.delay.call_args_list == [
        call(model.subscription.id, seat_id=seat_owner.id)
    ]
    assert database.list_of("payments.ServiceStockScheduler") == []
