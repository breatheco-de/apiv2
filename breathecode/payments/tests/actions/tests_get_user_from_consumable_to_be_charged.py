"""
Unit tests for actions.get_user_from_consumable_to_be_charged.

Mock-based tests (no DB) covering team-allowed vs not, PER_SEAT vs PER_TEAM strategies, and seat user fallback.
"""

import pytest
from types import SimpleNamespace
from django.contrib.auth.models import User
from django.utils import timezone
from dateutil.relativedelta import relativedelta

from breathecode.payments import actions
from breathecode.payments.models import (
    Currency,
    Service,
    ServiceItem,
    Subscription,
    SubscriptionBillingTeam,
    SubscriptionSeat,
    Consumable,
)
from breathecode.admissions.models import Academy, Country, City


class DummyTeamStrategy:
    class ConsumptionStrategy:
        PER_SEAT = "PER_SEAT"
        PER_TEAM = "PER_TEAM"


def build_consumable(*, resource=None, team=None, seat_user=None, is_team_allowed=True):
    """Build a minimal consumable stub referencing resource, team/seat, and service flags."""
    service = SimpleNamespace(is_team_allowed=is_team_allowed)
    service_item = SimpleNamespace(service=service)

    # Create a seat stub when a seat_user is provided OR strategy is PER_SEAT to avoid attribute errors
    seat = None
    if seat_user is not None or (
        team and getattr(team, "consumption_strategy", None) == DummyTeamStrategy.ConsumptionStrategy.PER_SEAT
    ):
        seat = SimpleNamespace(user=seat_user, billing_team=team)

    return SimpleNamespace(
        subscription=resource,
        plan_financing=None,
        subscription_billing_team=team,
        subscription_seat=seat,
        service_item=service_item,
    )


@pytest.mark.parametrize(
    "is_team_allowed, strategy, seat_has_user, expect_owner",
    [
        (False, None, False, True),  # not team allowed -> owner
        (True, DummyTeamStrategy.ConsumptionStrategy.PER_SEAT, True, False),  # per-seat -> seat user
        (True, DummyTeamStrategy.ConsumptionStrategy.PER_SEAT, False, True),  # per-seat without user -> owner
        (True, DummyTeamStrategy.ConsumptionStrategy.PER_TEAM, False, None),  # per-team -> None
    ],
)
def test_get_user_from_consumable_to_be_charged(is_team_allowed, strategy, seat_has_user, expect_owner):
    """Validate user resolution based on service allowance and team consumption strategy."""
    owner = SimpleNamespace(email="owner@example.com")
    seat_user = SimpleNamespace(email="seat@example.com") if seat_has_user else None

    # resource owner
    resource = SimpleNamespace(user=owner, __class__=SimpleNamespace(__name__="Subscription"))

    team = SimpleNamespace(consumption_strategy=strategy)
    c = build_consumable(resource=resource, team=team, seat_user=seat_user, is_team_allowed=is_team_allowed)

    out = actions.get_user_from_consumable_to_be_charged(c)

    if expect_owner is True:
        assert out is owner
    elif expect_owner is False:
        assert out is seat_user
    else:
        assert out is None


def test_get_user_from_consumable_to_be_charged__db_happy_path(database):
    """DB integration: when PER_SEAT and service allows teams, returns the seat user."""
    usd = Currency.objects.create(code="USD", name="US Dollar", decimals=2)
    user = User.objects.create(username="owner", email="owner@example.com")
    seat_user = User.objects.create(username="seat", email="seat@example.com")

    country = Country.objects.create(code="US", name="United States")
    city = City.objects.create(name="City", country=country)

    academy = Academy.objects.create(
        slug="a1",
        name="Academy 1",
        logo_url="https://example.com/logo.png",
        street_address="Addr 1",
        city=city,
        country=country,
        main_currency=usd,
    )

    # Minimal service with team allowed
    service = Service.objects.create(slug="svc-1", owner=academy)
    service_item = ServiceItem.objects.create(service=service, is_team_allowed=True)

    now = timezone.now()
    sub = Subscription.objects.create(
        user=user,
        academy=academy,
        paid_at=now - relativedelta(days=1),
        next_payment_at=now + relativedelta(days=29),
    )

    team = SubscriptionBillingTeam.objects.create(subscription=sub, name="Team 1", consumption_strategy="PER_SEAT")
    seat = SubscriptionSeat.objects.create(billing_team=team, user=seat_user, email=seat_user.email)

    c = Consumable.objects.create(
        service_item=service_item,
        user=seat_user,
        subscription=sub,
        subscription_billing_team=team,
        subscription_seat=seat,
    )

    out = actions.get_user_from_consumable_to_be_charged(c)
    assert out == seat_user
