"""
Unit tests for actions.validate_auto_recharge_service_units.

Mock-based tests (no DB) covering allow/deny decisions and error slugs:
- disabled, missing main currency
- academy-service-not-found, price-per-unit-not-found, price-per-unit-exceeded
- more-than-20-percent-left, infinite units, balance_above_threshold
- auto-recharge-threshold-reached, max-period-spend-reached
"""

import pytest
from types import SimpleNamespace
from django.contrib.auth.models import User
from django.utils import timezone
from dateutil.relativedelta import relativedelta

from breathecode.payments import actions
from breathecode.payments.models import Currency, Service, ServiceItem, AcademyService, Subscription
from breathecode.admissions.models import Academy, Country, City


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def build_resource(owner_email="owner@example.com"):
    """Build a minimal resource stub with defaults suitable for validation tests."""
    return SimpleNamespace(
        user=SimpleNamespace(email=owner_email),
        academy=SimpleNamespace(main_currency=SimpleNamespace(code="USD")),
        auto_recharge_enabled=True,
        recharge_threshold_amount=50.0,
        max_period_spend=None,
        recharge_amount=25.0,
        __class__=SimpleNamespace(__name__="Subscription"),
        id=1,
        get_current_period_spend=lambda service, user=None: 0.0,
    )


def build_consumable(resource, seat_user=None, team_strategy=None, is_team_allowed=True):
    """Build a minimal consumable pointing to the provided resource and service/team stubs."""
    service = SimpleNamespace(is_team_allowed=is_team_allowed)
    # actions.get_user_from_consumable_to_be_charged now reads from service_item.is_team_allowed
    service_item = SimpleNamespace(service=service, is_team_allowed=is_team_allowed)

    team = SimpleNamespace(consumption_strategy=team_strategy) if team_strategy else None
    seat = SimpleNamespace(user=seat_user, billing_team=team) if seat_user is not None else None

    return SimpleNamespace(
        subscription=resource,
        plan_financing=None,
        subscription_billing_team=team,
        subscription_seat=seat,
        service_item=service_item,
    )


def _patch_pricing_and_inventory(monkeypatch, price_per_unit, consumables):
    """Patch AcademyService price lookup and Consumable.list to control pricing/inventory."""

    class DummyQS:
        def first(self):
            return SimpleNamespace(price_per_unit=price_per_unit) if price_per_unit is not None else None

    monkeypatch.setattr(
        actions, "AcademyService", SimpleNamespace(objects=SimpleNamespace(filter=lambda **kw: DummyQS()))
    )
    monkeypatch.setattr(actions, "Consumable", SimpleNamespace(list=lambda user, service: consumables))


# -----------------------------------------------------------------------------
# Tests
# -----------------------------------------------------------------------------


def test_validate_auto_recharge_service_units__disabled_returns_none():
    """When auto-recharge is disabled, it should return (0.0, 0, None)."""
    resource = SimpleNamespace(auto_recharge_enabled=False)
    c = build_consumable(resource=resource)

    price, amount, error = actions.validate_auto_recharge_service_units(c)
    assert (price, amount, error) == (0.0, 0, None)


def test_validate_auto_recharge_service_units__missing_main_currency():
    """If main currency is missing, it should return the 'main-currency-not-found' slug."""
    resource = SimpleNamespace(auto_recharge_enabled=True, academy=SimpleNamespace(main_currency=None))
    c = build_consumable(resource=resource)

    price, amount, error = actions.validate_auto_recharge_service_units(c)
    assert (price, amount, error) == (0.0, 0, "main-currency-not-found")


def test_validate_auto_recharge_service_units__returns_price_and_units(monkeypatch):
    """Happy path: returns price per unit and units to buy given recharge_amount."""
    resource = build_resource()
    # Patch spend to small value
    monkeypatch.setattr(actions, "get_user_from_consumable_to_be_charged", lambda instance: SimpleNamespace(id=1))
    resource.get_current_period_spend = lambda service, user=None: 0.0

    # Provide at least one consumable to avoid division by zero in total/available
    _patch_pricing_and_inventory(
        monkeypatch,
        price_per_unit=10.0,
        consumables=[SimpleNamespace(how_many=5, service_item=SimpleNamespace(how_many=0))],
    )

    c = build_consumable(resource=resource)

    price, amount, error = actions.validate_auto_recharge_service_units(c)
    assert error is None
    assert price == 10.0
    assert amount == 2  # floor(25/10)


def test_validate_units__academy_service_not_found(monkeypatch):
    """When AcademyService lookup fails, return 'academy-service-not-found'."""
    resource = build_resource()
    c = build_consumable(resource)

    monkeypatch.setattr(actions, "get_user_from_consumable_to_be_charged", lambda instance: SimpleNamespace(id=1))
    _patch_pricing_and_inventory(monkeypatch, price_per_unit=None, consumables=[])

    price, amount, error = actions.validate_auto_recharge_service_units(c)
    assert (price, amount, error) == (0.0, 0, "academy-service-not-found")


def test_validate_units__price_per_unit_not_found(monkeypatch):
    """When price per unit is 0/invalid, return 'price-per-unit-not-found'."""
    resource = build_resource()
    c = build_consumable(resource)

    monkeypatch.setattr(actions, "get_user_from_consumable_to_be_charged", lambda instance: SimpleNamespace(id=1))
    _patch_pricing_and_inventory(monkeypatch, price_per_unit=0, consumables=[])

    price, amount, error = actions.validate_auto_recharge_service_units(c)
    assert (price, amount, error) == (0.0, 0, "price-per-unit-not-found")


def test_validate_units__price_per_unit_exceeded(monkeypatch):
    """When price > recharge_amount, return 'price-per-unit-exceeded'."""
    resource = build_resource()
    resource.recharge_amount = 5.0
    c = build_consumable(resource)

    monkeypatch.setattr(actions, "get_user_from_consumable_to_be_charged", lambda instance: SimpleNamespace(id=1))
    _patch_pricing_and_inventory(monkeypatch, price_per_unit=10.0, consumables=[])

    price, amount, error = actions.validate_auto_recharge_service_units(c)
    assert (price, amount, error) == (0.0, 0, "price-per-unit-exceeded")


def test_validate_units__more_than_20_percent_left(monkeypatch):
    """When remaining balance ratio is > 20%, should not auto-recharge."""
    resource = build_resource()
    c = build_consumable(resource)

    monkeypatch.setattr(actions, "get_user_from_consumable_to_be_charged", lambda instance: SimpleNamespace(id=1))
    _patch_pricing_and_inventory(
        monkeypatch,
        price_per_unit=10.0,
        consumables=[SimpleNamespace(how_many=7, service_item=SimpleNamespace(how_many=3))],  # 3/7>0.2
    )

    price, amount, error = actions.validate_auto_recharge_service_units(c)
    assert (price, amount, error) == (0.0, 0, "more-than-20-percent-left")


def test_validate_units__infinite_units(monkeypatch):
    """If any consumable has infinite units (-1), do not auto-recharge."""
    resource = build_resource()
    c = build_consumable(resource)

    monkeypatch.setattr(actions, "get_user_from_consumable_to_be_charged", lambda instance: SimpleNamespace(id=1))
    _patch_pricing_and_inventory(
        monkeypatch,
        price_per_unit=10.0,
        consumables=[SimpleNamespace(how_many=-1, service_item=SimpleNamespace(how_many=3))],
    )

    price, amount, error = actions.validate_auto_recharge_service_units(c)
    assert (price, amount, error) == (0.0, 0, None)


def test_validate_units__balance_above_threshold(monkeypatch):
    """If available balance * price > threshold, skip auto-recharge (no error)."""
    resource = build_resource()
    resource.recharge_threshold_amount = 10.0
    c = build_consumable(resource)

    monkeypatch.setattr(actions, "get_user_from_consumable_to_be_charged", lambda instance: SimpleNamespace(id=1))
    # Keep available*price high but total small to avoid triggering the 20% rule
    _patch_pricing_and_inventory(
        monkeypatch,
        price_per_unit=10.0,
        consumables=[SimpleNamespace(how_many=2, service_item=SimpleNamespace(how_many=0))],
    )

    price, amount, error = actions.validate_auto_recharge_service_units(c)
    assert (price, amount, error) == (0.0, 0, None)


def test_validate_units__threshold_reached(monkeypatch):
    """When current period spend >= threshold amount, return 'auto-recharge-threshold-reached'."""
    resource = build_resource()
    resource.recharge_threshold_amount = 5.0
    resource.get_current_period_spend = lambda service, user=None: 10.0
    c = build_consumable(resource)

    monkeypatch.setattr(actions, "get_user_from_consumable_to_be_charged", lambda instance: SimpleNamespace(id=1))
    _patch_pricing_and_inventory(monkeypatch, price_per_unit=10.0, consumables=[])

    price, amount, error = actions.validate_auto_recharge_service_units(c)
    assert (price, amount, error) == (0.0, 0, "auto-recharge-threshold-reached")


def test_validate_units__max_period_spend_reached(monkeypatch):
    """When current period spend >= max_period_spend, return 'max-period-spend-reached'."""
    resource = build_resource()
    resource.max_period_spend = 10.0
    resource.get_current_period_spend = lambda service, user=None: 10.0
    c = build_consumable(resource)

    monkeypatch.setattr(actions, "get_user_from_consumable_to_be_charged", lambda instance: SimpleNamespace(id=1))
    _patch_pricing_and_inventory(monkeypatch, price_per_unit=10.0, consumables=[])

    price, amount, error = actions.validate_auto_recharge_service_units(c)
    assert (price, amount, error) == (0.0, 0, "max-period-spend-reached")


def test_validate_auto_recharge_service_units__db_happy_path(database, monkeypatch):
    """DB integration: creates AcademyService in DB and validates happy path result."""
    # Minimal fixtures
    usd = Currency.objects.create(code="USD", name="US Dollar", decimals=2)
    owner = User.objects.create(username="owner", email="owner@example.com")
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

    svc = Service.objects.create(slug="svc-1", owner=academy)
    si = ServiceItem.objects.create(service=svc, is_team_allowed=False)
    AcademyService.objects.create(academy=academy, currency=usd, service=svc, price_per_unit=10.0)

    now = timezone.now()
    sub = Subscription.objects.create(
        user=owner,
        academy=academy,
        paid_at=now - relativedelta(days=1),
        next_payment_at=now + relativedelta(days=29),
        auto_recharge_enabled=True,
        recharge_threshold_amount=50.0,
        recharge_amount=25.0,
    )

    # Ensure Python type is float to avoid Decimal/float division in actions logic
    sub.recharge_amount = 25.0

    # Build a real-ish consumable stub: pass real ServiceItem so `.is_team_allowed` exists
    c = SimpleNamespace(
        subscription=sub,
        plan_financing=None,
        service_item=si,
        subscription_seat=None,
        subscription_billing_team=None,
    )

    # Patch get_user_from_consumable_to_be_charged for spend calculation
    monkeypatch.setattr(actions, "get_user_from_consumable_to_be_charged", lambda instance: owner)
    # Keep Consumable.list simple to avoid full inventory setup
    monkeypatch.setattr(
        actions,
        "Consumable",
        SimpleNamespace(
            list=lambda user, service: [SimpleNamespace(how_many=5, service_item=SimpleNamespace(how_many=0))]
        ),
    )

    price, amount, error = actions.validate_auto_recharge_service_units(c)
    assert error is None
    assert price == 10.0
    assert amount == 2
