"""
Unit tests for actions.get_user_from_consumable_to_be_charged.

Mock-based tests (no DB) covering team-allowed vs not, PER_SEAT vs PER_TEAM strategies, and seat user fallback.
"""

import pytest
from types import SimpleNamespace

from breathecode.payments import actions


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
