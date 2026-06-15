from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from breathecode.payments.management.commands.backfill_invoice_amount_breakdown import Command
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode

UTC_NOW = timezone.now()


@pytest.fixture(autouse=True)
def setup(db):
    yield


@patch(
    "breathecode.payments.management.commands.backfill_invoice_amount_breakdown.calculate_invoice_breakdown",
    MagicMock(return_value={"plans": {"plan-a": {"amount": 50.0, "currency": "USD"}}, "service-items": {}}),
)
def test_backfill_updates_invoice_without_breakdown(mock_calculate, bc: Breathecode):
    model = bc.database.create(
        academy=1,
        currency=1,
        bag={"chosen_period": "MONTH", "how_many_installments": 0},
        invoice={
            "paid_at": UTC_NOW,
            "status": "FULFILLED",
            "academy_id": 1,
            "amount": 50.0,
            "amount_breakdown": None,
        },
    )

    Command().handle()

    invoice = bc.database.get("payments.Invoice", model.invoice.id, dict=False)
    assert invoice.amount_breakdown == {
        "plans": {"plan-a": {"amount": 50.0, "currency": "USD"}},
        "service-items": {},
    }
    mock_calculate.assert_called_once()


@patch(
    "breathecode.payments.management.commands.backfill_invoice_amount_breakdown.calculate_invoice_breakdown",
    MagicMock(),
)
def test_backfill_dry_run_does_not_persist(mock_calculate, bc: Breathecode):
    model = bc.database.create(
        academy=1,
        currency=1,
        bag={"chosen_period": "MONTH"},
        invoice={
            "paid_at": UTC_NOW,
            "status": "FULFILLED",
            "academy_id": 1,
            "amount": 50.0,
            "amount_breakdown": None,
        },
    )

    Command().handle(dry_run=True)

    invoice = bc.database.get("payments.Invoice", model.invoice.id, dict=False)
    assert invoice.amount_breakdown is None
    mock_calculate.assert_called_once()


@patch(
    "breathecode.payments.management.commands.backfill_invoice_amount_breakdown.calculate_invoice_breakdown",
    MagicMock(),
)
def test_backfill_skips_invoice_with_existing_breakdown(mock_calculate, bc: Breathecode):
    existing = {"plans": {"plan-a": {"amount": 50.0, "currency": "USD"}}, "service-items": {}}
    bc.database.create(
        academy=1,
        currency=1,
        bag={"chosen_period": "MONTH"},
        invoice={
            "paid_at": UTC_NOW,
            "status": "FULFILLED",
            "academy_id": 1,
            "amount": 50.0,
            "amount_breakdown": existing,
        },
    )

    Command().handle()

    mock_calculate.assert_not_called()


@patch(
    "breathecode.payments.management.commands.backfill_invoice_amount_breakdown.calculate_invoice_breakdown",
    MagicMock(return_value={"plans": {}, "service-items": {}}),
)
def test_backfill_respects_years_filter(mock_calculate, bc: Breathecode):
    from dateutil.relativedelta import relativedelta

    bc.database.create(
        academy=1,
        currency=1,
        bag={"chosen_period": "MONTH"},
        invoice={
            "paid_at": UTC_NOW - relativedelta(years=2),
            "status": "FULFILLED",
            "academy_id": 1,
            "amount": 50.0,
            "amount_breakdown": None,
        },
    )

    Command().handle(years=1)

    mock_calculate.assert_not_called()


@patch(
    "breathecode.payments.management.commands.backfill_invoice_amount_breakdown.calculate_invoice_breakdown",
    MagicMock(),
)
def test_backfill_skips_zero_amount_invoices(mock_calculate, bc: Breathecode):
    bc.database.create(
        academy=1,
        currency=1,
        bag={"chosen_period": "MONTH"},
        invoice={
            "paid_at": UTC_NOW,
            "status": "FULFILLED",
            "academy_id": 1,
            "amount": 0.0,
            "amount_breakdown": None,
        },
    )

    Command().handle()

    mock_calculate.assert_not_called()
