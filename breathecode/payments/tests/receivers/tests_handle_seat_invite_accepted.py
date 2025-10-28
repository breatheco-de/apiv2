import types
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

# Unit under test
from breathecode.payments.receivers import handle_seat_invite_accepted as uut
import breathecode.payments.receivers as receivers


class DummyPlans:
    def __init__(self, plan):
        self._plan = plan

    def first(self):
        return self._plan

    def all(self):
        return [self._plan]


class DummySubscription:
    def __init__(self, _id: int, plan):
        self.id = _id
        self.plans = DummyPlans(plan)


class DummyBillingTeam:
    def __init__(self, subscription, consumption_strategy):
        self.subscription = subscription
        self.consumption_strategy = consumption_strategy


class DummySeat:
    def __init__(self, _id: int, email: str, billing_team: DummyBillingTeam):
        self.id = _id
        self.email = email
        self.user = None
        self.billing_team = billing_team
        self._saved = False

    def save(self):
        self._saved = True


class DummyQS(list):
    def select_related(self, *args, **kwargs):
        return self


class DummyManager:
    def __init__(self, seats):
        self.seats = seats

    def filter(self, *args, **kwargs):
        return DummyQS(self.seats)


@pytest.fixture(autouse=True)
def patch_strategies(monkeypatch):
    """Patch consumption strategy enums on Plan and SubscriptionBillingTeam so tests don't import real models."""
    # Patch strategy enums used in logic
    monkeypatch.setattr(
        receivers.Plan,
        "ConsumptionStrategy",
        SimpleNamespace(PER_SEAT="PER_SEAT", PER_TEAM="PER_TEAM", BOTH="BOTH"),
        raising=False,
    )
    monkeypatch.setattr(
        receivers.SubscriptionBillingTeam,
        "ConsumptionStrategy",
        SimpleNamespace(PER_SEAT="PER_SEAT", PER_TEAM="PER_TEAM"),
        raising=False,
    )


def make_invite(email: str, user_id: int = 1, status: str = "ACCEPTED"):
    """Create a minimal invite-like object with the attributes the handler reads (email, user, user_id, status)."""
    user = SimpleNamespace(email=email)
    invite = SimpleNamespace(email=email, user=user, user_id=user_id, status=status)
    return invite


def test_noop_when_status_not_accepted(monkeypatch):
    """Ensure the handler performs no operation if invite.status is not ACCEPTED (e.g., PENDING)."""
    # Arrange
    called = MagicMock()
    dummy_task = types.SimpleNamespace(build_service_stock_scheduler_from_subscription=SimpleNamespace(delay=called))
    monkeypatch.setattr(receivers, "tasks", dummy_task)

    # No DB lookups should happen; ensure objects not present causes no crash
    monkeypatch.setattr(receivers.SubscriptionSeat, "objects", DummyManager([]), raising=False)

    invite = make_invite("member@example.com", user_id=2, status="PENDING")

    # Act
    uut(None, invite)

    # Assert
    called.assert_not_called()


@pytest.mark.django_db
def test_integration_binds_seat_and_assigns_consumables_when_per_seat(monkeypatch, database):
    """
    Integration test
    Given a real Subscription, BillingTeam with PER_SEAT strategy, and a pending SubscriptionSeat (user=None)
    When handle_seat_invite_accepted is invoked for an ACCEPTED invite matching the seat email
    Then the seat is bound to the real user (email lowercased) and existing consumables are assigned to the user.
    """
    from django.utils import timezone
    from datetime import timedelta
    from django.contrib.auth.models import User
    from breathecode.admissions.models import Academy, Country, City
    from breathecode.payments.models import (
        Subscription,
        SubscriptionBillingTeam,
        SubscriptionSeat,
        Consumable,
        Service,
        ServiceItem,
    )

    # Patch actions.grant_student_capabilities
    grant_capabilities_called = MagicMock()
    monkeypatch.setattr(receivers.actions, "grant_student_capabilities", grant_capabilities_called)

    # Real owner and subscription
    owner = User.objects.create(username="owner", email="owner@example.com")
    now = timezone.now()

    # Minimal academy required by Subscription model
    country = Country.objects.create(code="US", name="United States")
    city = City.objects.create(name="Miami", country=country)

    academy = Academy.objects.create(
        slug="academy-x",
        name="Academy X",
        logo_url="https://example.com/logo.png",
        street_address="123 Main St",
        country=country,
        city=city,
    )

    subscription = Subscription.objects.create(
        user=owner,
        academy=academy,
        paid_at=now,
        next_payment_at=now + timedelta(days=30),
    )

    # Attach a dummy plans manager to any Subscription instance so receiver can read plan strategy
    plan = SimpleNamespace(consumption_strategy=receivers.Plan.ConsumptionStrategy.PER_SEAT)
    monkeypatch.setattr(Subscription, "plans", property(lambda self: DummyPlans(plan)), raising=False)

    team = SubscriptionBillingTeam.objects.create(
        subscription=subscription,
        name="Team X",
        consumption_strategy=receivers.SubscriptionBillingTeam.ConsumptionStrategy.PER_SEAT,
    )

    seat = SubscriptionSeat.objects.create(billing_team=team, email="Member@Example.com")

    # Create a consumable with user=None (waiting for invitation acceptance)
    # Must have subscription_billing_team set since user is None (validation requirement)
    service = Service.objects.create(slug="test-service", type="COHORT_SET")
    service_item = ServiceItem.objects.create(service=service, how_many=10, unit_type="UNIT")
    consumable = Consumable.objects.create(
        subscription=subscription,
        subscription_seat=seat,
        subscription_billing_team=team,  # Required when user=None
        user=None,  # Not assigned yet (waiting for invitation acceptance)
        service_item=service_item,
        cohort_set_id=None,
        how_many=1,
    )

    # Invite with matching email: use a real Django User for FK assignment
    member = User.objects.create(username="member", email="member@example.com")
    invite = SimpleNamespace(email=member.email, user=member, user_id=member.id, status="ACCEPTED")

    # Act
    uut(None, invite)

    # Assert: seat bound and normalized email
    seat.refresh_from_db()
    assert seat.user == invite.user
    assert seat.email == invite.user.email.lower()

    # Assert: consumable assigned to user
    consumable.refresh_from_db()
    assert consumable.user == member

    # Assert: student capabilities granted
    grant_capabilities_called.assert_called()


def test_updates_consumables_and_binds_when_per_seat(monkeypatch):
    """Bind seat to user, normalize email, and update consumables when strategy enables per-seat issuance."""
    # Arrange
    # Mock Consumable.objects.filter().update() to track consumable updates
    mock_consumable_qs = MagicMock()
    mock_consumable_qs.update = MagicMock()
    mock_consumable_manager = MagicMock()
    mock_consumable_manager.filter.return_value = mock_consumable_qs
    monkeypatch.setattr(receivers.Consumable, "objects", mock_consumable_manager, raising=False)

    # Mock actions.grant_student_capabilities
    grant_capabilities_called = MagicMock()
    monkeypatch.setattr(receivers.actions, "grant_student_capabilities", grant_capabilities_called)

    plan = SimpleNamespace(consumption_strategy=receivers.Plan.ConsumptionStrategy.BOTH)
    subscription = DummySubscription(1, plan)
    team = DummyBillingTeam(
        subscription, consumption_strategy=receivers.SubscriptionBillingTeam.ConsumptionStrategy.PER_TEAM
    )
    seat = DummySeat(99, "Member@Example.com", team)

    monkeypatch.setattr(receivers.SubscriptionSeat, "objects", DummyManager([seat]), raising=False)

    invite = make_invite("member@example.com", user_id=7, status="ACCEPTED")

    # Act
    uut(None, invite)

    # Assert
    assert seat.user is invite.user
    assert seat.email == invite.user.email.lower()
    assert seat._saved is True
    # Assert consumables were updated with the new user
    mock_consumable_manager.filter.assert_called_once()
    mock_consumable_qs.update.assert_called_once_with(user=invite.user)
    # Assert student capabilities granted
    grant_capabilities_called.assert_called_once_with(invite.user, plan)


def test_does_not_update_consumables_when_per_team_only(monkeypatch):
    """Bind seat to user but do not update consumables when only PER_TEAM strategy is effective."""
    # Arrange
    # Mock Consumable.objects.filter().update() to track consumable updates
    mock_consumable_qs = MagicMock()
    mock_consumable_qs.update = MagicMock()
    mock_consumable_manager = MagicMock()
    mock_consumable_manager.filter.return_value = mock_consumable_qs
    monkeypatch.setattr(receivers.Consumable, "objects", mock_consumable_manager, raising=False)

    # Mock actions.grant_student_capabilities
    grant_capabilities_called = MagicMock()
    monkeypatch.setattr(receivers.actions, "grant_student_capabilities", grant_capabilities_called)

    plan = SimpleNamespace(consumption_strategy=receivers.Plan.ConsumptionStrategy.PER_SEAT)
    subscription = DummySubscription(2, plan)
    team = DummyBillingTeam(
        subscription, consumption_strategy=receivers.SubscriptionBillingTeam.ConsumptionStrategy.PER_TEAM
    )
    seat = DummySeat(100, "member@example.com", team)

    monkeypatch.setattr(receivers.SubscriptionSeat, "objects", DummyManager([seat]), raising=False)

    invite = make_invite("member@example.com", user_id=10, status="ACCEPTED")

    # Act
    uut(None, invite)

    # Assert
    assert seat.user is invite.user
    assert seat._saved is True
    # Assert consumables were NOT updated (PER_TEAM strategy)
    mock_consumable_manager.filter.assert_not_called()
    mock_consumable_qs.update.assert_not_called()
    # Assert capabilities were NOT granted (PER_TEAM strategy)
    grant_capabilities_called.assert_not_called()
