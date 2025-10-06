import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock

from dateutil.relativedelta import relativedelta
from django.utils import timezone
from django.contrib.auth.models import User
from django.apps import apps

from breathecode.payments.models import (
    SubscriptionBillingTeam,
    Currency,
    Subscription,
    Bag,
    Invoice as _InvoiceModel,
)
from breathecode.admissions.models import Academy, Country, City


# -----------------------------------------------------------------------------
# Global patches to avoid any DB access and ensure enum presence
# -----------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _patch_invoice_manager(monkeypatch):
    """Patch Invoice class and its manager to avoid DB and capture filter kwargs."""

    class _Status:
        FULFILLED = "FULFILLED"

    class _DummyQS:
        def __init__(self):
            self.first_filter_args = None
            self.first_filter_kwargs = None
            self.second_filter_kwargs = None

        def filter(self, *args, **kwargs):
            # First call stores args/kwargs and returns self for chaining
            if self.first_filter_kwargs is None:
                self.first_filter_args = args
                self.first_filter_kwargs = kwargs
                return self
            # Second call stores period_end kwargs and returns self
            self.second_filter_kwargs = kwargs
            return self

        def aggregate(self, **kwargs):
            # Return a default total unless overridden by test
            return {"total": getattr(self, "_total", None)}

    dummy_qs = _DummyQS()

    class _InvoiceObjects:
        def filter(self, *args, **kwargs):
            # Emulate Django manager filter: returns chainable QS
            return dummy_qs.filter(*args, **kwargs)

    DummyInvoice = SimpleNamespace(Status=_Status, objects=_InvoiceObjects())

    monkeypatch.setattr("breathecode.payments.models.Invoice", DummyInvoice, raising=True)

    # Expose for tests to inspect
    return dummy_qs


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _team_self(period_start, period_end, user_id=1):
    """Build a self-like object for SubscriptionBillingTeam.get_current_period_spend."""

    def _periods_method():
        return period_start, period_end

    self_like = SimpleNamespace()
    self_like.subscription = SimpleNamespace(user=SimpleNamespace(id=user_id))
    self_like.get_current_monthly_period_dates = _periods_method
    return self_like


# -----------------------------------------------------------------------------
# Tests
# -----------------------------------------------------------------------------


def test_team_spend_uses_fulfilled_and_paid_at_window(_patch_invoice_manager):
    now_time = timezone.now()
    start = now_time - relativedelta(days=10)
    end = now_time + relativedelta(days=20)

    # Access the patched Invoice dummy via fixture return
    invoice_qs = _patch_invoice_manager
    team = _team_self(start, end)

    # Call the real method with a self-like object
    total = SubscriptionBillingTeam.get_current_period_spend(team)
    assert total == 0.0  # default None -> 0.0

    # The first filter must include status FULFILLED and paid_at >= start, plus team filter
    fk = invoice_qs.first_filter_kwargs
    assert fk["status"] == "FULFILLED"
    assert fk["paid_at__gte"] == start
    assert fk["subscription_billing_team"] is team

    # The second filter should limit by end using paid_at__lt
    sk = invoice_qs.second_filter_kwargs
    assert sk == {"paid_at__lt": end}


def test_team_spend_db_happy_path(database, monkeypatch):
    """DB integration: create real rows and ensure ORM path runs and sums paid invoices for team."""
    # Restore real Invoice class (autouse fixture replaces it)
    real_invoice = apps.get_model("payments", "Invoice")
    monkeypatch.setattr("breathecode.payments.models.Invoice", real_invoice, raising=True)

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
        paid_at=now - relativedelta(days=5),
        next_payment_at=now + relativedelta(days=25),
    )
    team = SubscriptionBillingTeam.objects.create(subscription=sub, name="Team 1")

    bag = Bag.objects.create(user=user, academy=academy, currency=usd)
    inv = real_invoice.objects.create(
        user=user,
        academy=academy,
        currency=usd,
        bag=bag,
        amount=77.77,
        paid_at=now - relativedelta(days=2),
        status=real_invoice.Status.FULFILLED,
        subscription_billing_team=team,
    )

    # Link invoice to subscription via M2M to be consistent (not strictly required for team path)
    sub.invoices.add(inv)

    total = team.get_current_period_spend()
    assert total == pytest.approx(77.77)


def test_team_spend_filters_and_returns_total(monkeypatch):
    now_time = timezone.now()
    start = now_time - relativedelta(days=2)

    # Build a new dummy_qs with a preset total and expose it to the manager
    class _Status:
        FULFILLED = "FULFILLED"

    class _DummyQS2:
        def __init__(self):
            self.first_filter_args = None
            self.first_filter_kwargs = None
            self.second_filter_kwargs = None
            self._total = 123.45

        def filter(self, *args, **kwargs):
            if self.first_filter_kwargs is None:
                self.first_filter_args = args
                self.first_filter_kwargs = kwargs
                return self
            self.second_filter_kwargs = kwargs
            return self

        def aggregate(self, **kwargs):
            return {"total": self._total}

    dummy_qs2 = _DummyQS2()

    class _InvoiceObjects2:
        def filter(self, *args, **kwargs):
            return dummy_qs2.filter(*args, **kwargs)

    DummyInvoice2 = SimpleNamespace(Status=_Status, objects=_InvoiceObjects2())
    monkeypatch.setattr("breathecode.payments.models.Invoice", DummyInvoice2, raising=True)

    end = start + relativedelta(months=1)
    team = _team_self(start, end)

    result = SubscriptionBillingTeam.get_current_period_spend(team)
    assert result == 123.45

    # Assert first filter kwargs
    fk = dummy_qs2.first_filter_kwargs
    assert fk["status"] == DummyInvoice2.Status.FULFILLED
    assert fk["paid_at__gte"] == start
    assert fk["subscription_billing_team"] is team

    # Assert second filter uses paid_at__lt
    sk = dummy_qs2.second_filter_kwargs
    assert sk == {"paid_at__lt": end}
