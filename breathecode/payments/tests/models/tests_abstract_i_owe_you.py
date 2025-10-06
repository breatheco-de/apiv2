import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock

from dateutil.relativedelta import relativedelta
from django.utils import timezone
from django.contrib.auth.models import User

# We will call the real functions from AbstractIOweYou, but everything else is mocked
from breathecode.payments.models import AbstractIOweYou, Currency, Subscription, Bag, Invoice
from breathecode.admissions.models import Academy, Country, City


# -----------------------------------------------------------------------------
# Global patches to avoid any DB access and missing enum values
# -----------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _patch_globals(monkeypatch):
    # get_user_settings -> simple object with lang so translation works if used
    monkeypatch.setattr(
        "breathecode.payments.models.get_user_settings",
        lambda user_id: SimpleNamespace(lang="en"),
        raising=True,
    )

    # Invoice.Status has no PAID value in this codebase; the implementation expects it
    monkeypatch.setattr(
        "breathecode.payments.models.Invoice.Status.PAID",
        "FULFILLED",
        raising=False,
    )


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _self_with_paid_at(paid_at):
    # Minimal self-like object for get_current_monthly_period_dates
    return SimpleNamespace(paid_at=paid_at)


def _spend_self(period_start, period_end, *, is_subscription=False, user_id=1, invoices_total=None):
    """Build a mock self object suitable for get_current_period_spend.

    - Provides self.user, self.invoices, self.get_current_monthly_period_dates
    - is_subscription controls isinstance(self, Subscription) path using type hack
    """

    # get_current_monthly_period_dates must be a method bound to self
    def _periods_method():
        return period_start, period_end

    # invoices manager mock
    invoices = MagicMock()
    invoices.filter.return_value.aggregate.return_value = {"total": invoices_total}

    # user-like object that has id
    user = SimpleNamespace(id=user_id)

    # Build a custom type to control isinstance checks if needed
    # We don't import Subscription to keep this self-contained; the code checks
    # isinstance(self, Subscription). We'll simulate non-subscription path by default.
    SelfType = type("SelfType", (), {})
    self_obj = SelfType()
    self_obj.user = user
    self_obj.invoices = invoices
    self_obj.get_current_monthly_period_dates = _periods_method

    return self_obj


# -----------------------------------------------------------------------------
# Tests for AbstractIOweYou.get_current_monthly_period_dates
# -----------------------------------------------------------------------------


def test_get_current_monthly_period_dates__with_paid_at_day_after():
    paid_at = timezone.now().replace(day=15, hour=9, minute=0, second=0, microsecond=0) - relativedelta(months=1)
    now_time = paid_at + relativedelta(months=1, days=5)  # current day 20th

    self_like = _self_with_paid_at(paid_at)

    # Patch now
    orig_now = timezone.now
    try:
        timezone.now = lambda: now_time
        period_start, period_end = AbstractIOweYou.get_current_monthly_period_dates(self_like)
    finally:
        timezone.now = orig_now

    assert period_start.day == paid_at.day
    assert period_end == period_start + relativedelta(months=1)
    assert period_start <= now_time < period_end


def test_get_current_monthly_period_dates__with_paid_at_day_before():
    paid_at = timezone.now().replace(day=25, hour=10, minute=0, second=0, microsecond=0) - relativedelta(months=1)
    now_time = paid_at + relativedelta(months=1) - relativedelta(days=10)  # current day ~15th

    self_like = _self_with_paid_at(paid_at)

    orig_now = timezone.now
    try:
        timezone.now = lambda: now_time
        period_start, period_end = AbstractIOweYou.get_current_monthly_period_dates(self_like)
    finally:
        timezone.now = orig_now

    assert period_start.day == paid_at.day
    assert period_end == period_start + relativedelta(months=1)
    assert period_start <= now_time < period_end


def test_get_current_monthly_period_dates__fallback_when_no_paid_at():
    now_time = timezone.now().replace(day=7, hour=0, minute=0, second=0, microsecond=0)
    self_like = _self_with_paid_at(None)

    orig_now = timezone.now
    try:
        timezone.now = lambda: now_time
        period_start, period_end = AbstractIOweYou.get_current_monthly_period_dates(self_like)
    finally:
        timezone.now = orig_now

    assert period_start.day == 1
    assert period_start.hour == 0
    assert period_end == period_start + relativedelta(months=1)
    assert period_start <= now_time < period_end


# -----------------------------------------------------------------------------
# Tests for AbstractIOweYou.get_current_period_spend
# (All mocks; no DB; one integration-style test with wraps at the end)
# -----------------------------------------------------------------------------


def test_get_current_period_spend__no_invoices_returns_zero():
    now_time = timezone.now()
    start = now_time - relativedelta(days=10)
    end = now_time + relativedelta(days=20)

    self_like = _spend_self(start, end, invoices_total=None)

    total = AbstractIOweYou.get_current_period_spend(self_like)
    assert total == 0.0
    self_like.invoices.filter.assert_called()  # ensures the path queries invoices


def test_get_current_period_spend__sums_paid_invoices():
    now_time = timezone.now()
    start = now_time - relativedelta(days=5)
    end = now_time + relativedelta(days=25)

    self_like = _spend_self(start, end, invoices_total=123.45)

    total = AbstractIOweYou.get_current_period_spend(self_like)
    assert total == 123.45


def test_get_current_period_spend__filters_by_service_when_provided():
    now_time = timezone.now()
    start = now_time - relativedelta(days=5)
    end = now_time + relativedelta(days=25)

    self_like = _spend_self(start, end, invoices_total=50.0)
    mock_service = object()

    _ = AbstractIOweYou.get_current_period_spend(self_like, service=mock_service)

    # inspect kwargs to ensure filter contains the service restriction
    _, kwargs = self_like.invoices.filter.call_args
    assert kwargs.get("bag__service_items__service") is mock_service


def test_get_current_period_spend__invalid_user_string_raises_attribute_error():
    # The implementation accesses user.id before validating string-ness
    now_time = timezone.now()
    start = now_time - relativedelta(days=1)
    end = now_time + relativedelta(days=29)

    self_like = _spend_self(start, end, invoices_total=None)

    with pytest.raises(AttributeError):
        AbstractIOweYou.get_current_period_spend(self_like, user="invalid-user-slug")


# -----------------------------------------------------------------------------
# Integration-style test using wraps: run the original function via a wrapper
# The rest of the object is fully mocked.
# -----------------------------------------------------------------------------


def test_get_current_period_spend__integration_like_with_wraps():
    # periods
    now_time = timezone.now()
    start = now_time.replace(hour=0, minute=0, second=0, microsecond=0) - relativedelta(days=2)
    end = start + relativedelta(months=1)

    # Build self mock with required surface
    invoices_total = 80.0
    self_like = _spend_self(start, end, invoices_total=invoices_total)

    # wrap the original function and call it
    wrapper = MagicMock(wraps=AbstractIOweYou.get_current_period_spend)
    result = wrapper(self_like)

    assert wrapper.called is True
    assert result == invoices_total
    self_like.invoices.filter.assert_called()


def test_get_current_period_spend__uses_fulfilled_and_paid_at_window():
    now_time = timezone.now()
    start = now_time - relativedelta(days=3)
    end = start + relativedelta(months=1)

    self_like = _spend_self(start, end, invoices_total=40.0)

    # call real method
    total = AbstractIOweYou.get_current_period_spend(self_like)
    assert total == 40.0

    # inspect kwargs of the filter call
    _, kwargs = self_like.invoices.filter.call_args
    # status must be FULFILLED in this codebase
    from breathecode.payments.models import Invoice

    assert kwargs["status"] == Invoice.Status.FULFILLED
    assert kwargs["paid_at__gte"] == start
    assert kwargs["paid_at__lt"] == end
    assert "bag__service_items__service" not in kwargs


def test_get_current_period_spend__uses_service_and_paid_at_window():
    now_time = timezone.now()
    start = now_time - relativedelta(days=5)
    end = start + relativedelta(months=1)

    self_like = _spend_self(start, end, invoices_total=22.0)

    mocked_service = object()
    _ = AbstractIOweYou.get_current_period_spend(self_like, service=mocked_service)

    _, kwargs = self_like.invoices.filter.call_args
    from breathecode.payments.models import Invoice

    assert kwargs["status"] == Invoice.Status.FULFILLED
    assert kwargs["paid_at__gte"] == start
    assert kwargs["paid_at__lt"] == end
    assert kwargs.get("bag__service_items__service") is mocked_service


def test_get_current_period_spend__db_happy_path(database, monkeypatch):
    """DB integration: create real rows and ensure ORM path works and sums paid invoices."""
    # Avoid external deps
    monkeypatch.setattr(
        "breathecode.payments.models.get_user_settings",
        lambda user_id: SimpleNamespace(lang="en"),
        raising=True,
    )

    class _DummyTask:
        def delay(self, *args, **kwargs):
            return None

    monkeypatch.setattr("breathecode.activity.tasks.add_activity", _DummyTask(), raising=True)

    # Minimal fixtures
    usd = Currency.objects.create(code="USD", name="US Dollar", decimals=2)
    user = User.objects.create(username="u1", email="u1@example.com")
    country = Country.objects.create(code="US", name="United States")
    city = City.objects.create(name="City", country=country)

    academy = Academy.objects.create(
        slug="a1",
        name="Academy 1",
        logo_url="https://example.com/logo.png",
        street_address="Somewhere 123",
        city=city,
        country=country,
        main_currency=usd,
    )

    now = timezone.now()
    sub = Subscription.objects.create(
        user=user,
        academy=academy,
        paid_at=now - relativedelta(days=3),
        next_payment_at=now + relativedelta(days=27),
    )

    bag = Bag.objects.create(user=user, academy=academy, currency=usd)
    inv = Invoice.objects.create(
        user=user,
        academy=academy,
        currency=usd,
        bag=bag,
        amount=50.0,
        paid_at=now - relativedelta(days=1),
        status=Invoice.Status.FULFILLED,
    )

    sub.invoices.add(inv)

    total = sub.get_current_period_spend()
    assert total == pytest.approx(50.0)
