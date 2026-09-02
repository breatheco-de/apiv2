from unittest.mock import MagicMock

import capyc.pytest as capy
import pytest
from dateutil.relativedelta import relativedelta
from django.utils import timezone

from breathecode.payments import tasks
from breathecode.payments.management.commands.backfill_plan_financing_created_by_admin import Command
from breathecode.payments.models import Invoice, PlanFinancing

UTC_NOW = timezone.now()

pytestmark = pytest.mark.usefixtures("db")


@pytest.fixture(autouse=True)
def patch_charge(monkeypatch: pytest.MonkeyPatch):
    delay = MagicMock()
    monkeypatch.setattr(tasks.charge_plan_financing, "delay", delay)
    monkeypatch.setattr("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    return delay


def _create_plan_with_proof(database: capy.Database, *, overdue=True, email="staff@example.com", status="ACTIVE"):
    next_payment_at = UTC_NOW - relativedelta(days=9) if overdue else UTC_NOW + relativedelta(days=20)
    model = database.create(
        academy=1,
        user={"email": email},
        proof_of_payment=1,
        plan={"is_renewable": False},
        plan_financing={
            "valid_until": UTC_NOW + relativedelta(months=6),
            "next_payment_at": next_payment_at,
            "monthly_price": 100.0,
            "how_many_installments": 12,
            "installments_paid": 1,
            "plan_expires_at": UTC_NOW + relativedelta(months=12),
            "status": status,
            "created_by_admin": False,
        },
        bag={"how_many_installments": 12, "was_delivered": True, "type": "BAG"},
        invoice={
            "paid_at": UTC_NOW - relativedelta(months=2),
            "amount": 100.0,
            "status": "FULFILLED",
            "proof_id": 1,
            "stripe_id": None,
        },
    )
    model.plan_financing.invoices.add(model.invoice)
    return model


def test_marks_plan_with_proof_and_queues_overdue_charge(database: capy.Database, patch_charge):
    model = _create_plan_with_proof(database)

    Command().handle(dry_run=False, email=None, plan_financing_id=None)

    model.plan_financing.refresh_from_db()
    assert model.plan_financing.created_by_admin is True
    patch_charge.assert_called_once_with(model.plan_financing.id)


def test_marks_when_only_a_later_invoice_has_proof(database: capy.Database, patch_charge):
    model = database.create(
        academy=1,
        proof_of_payment=1,
        plan={"is_renewable": False},
        plan_financing={
            "valid_until": UTC_NOW + relativedelta(months=6),
            "next_payment_at": UTC_NOW + relativedelta(days=20),
            "monthly_price": 100.0,
            "how_many_installments": 12,
            "installments_paid": 2,
            "plan_expires_at": UTC_NOW + relativedelta(months=12),
            "status": "ACTIVE",
            "created_by_admin": False,
        },
        bag={"how_many_installments": 12, "was_delivered": True, "type": "BAG"},
        invoice={
            "paid_at": UTC_NOW - relativedelta(months=2),
            "amount": 100.0,
            "status": "FULFILLED",
            "proof_id": None,
            "stripe_id": "ch_checkout",
        },
    )
    model.plan_financing.invoices.add(model.invoice)
    model.invoice.proof = None
    model.invoice.save(update_fields=["proof"])

    later = Invoice(
        user=model.invoice.user,
        academy=model.invoice.academy,
        currency=model.invoice.currency,
        bag=model.bag,
        amount=50.0,
        paid_at=UTC_NOW - relativedelta(days=5),
        status="FULFILLED",
        proof=model.proof_of_payment,
    )
    later.save()
    model.plan_financing.invoices.add(later)

    Command().handle(dry_run=False, email=None, plan_financing_id=None)

    model.plan_financing.refresh_from_db()
    assert model.plan_financing.created_by_admin is True
    patch_charge.assert_not_called()


def test_dry_run_does_not_mark_or_charge(database: capy.Database, patch_charge):
    model = _create_plan_with_proof(database)

    Command().handle(dry_run=True, email=None, plan_financing_id=None)

    model.plan_financing.refresh_from_db()
    assert model.plan_financing.created_by_admin is False
    patch_charge.assert_not_called()


def test_marks_but_does_not_charge_when_next_payment_is_in_the_future(database: capy.Database, patch_charge):
    model = _create_plan_with_proof(database, overdue=False)

    Command().handle(dry_run=False, email=None, plan_financing_id=None)

    model.plan_financing.refresh_from_db()
    assert model.plan_financing.created_by_admin is True
    patch_charge.assert_not_called()


def test_skips_checkout_plan_without_proof(database: capy.Database, patch_charge):
    model = database.create(
        academy=1,
        plan={"is_renewable": False},
        plan_financing={
            "valid_until": UTC_NOW + relativedelta(months=6),
            "next_payment_at": UTC_NOW - relativedelta(days=9),
            "monthly_price": 100.0,
            "how_many_installments": 12,
            "installments_paid": 1,
            "plan_expires_at": UTC_NOW + relativedelta(months=12),
            "status": "ACTIVE",
            "created_by_admin": False,
        },
        bag={"how_many_installments": 12, "was_delivered": True, "type": "BAG"},
        invoice={
            "paid_at": UTC_NOW - relativedelta(months=2),
            "amount": 100.0,
            "status": "FULFILLED",
            "proof_id": None,
            "stripe_id": "ch_checkout",
        },
    )
    model.plan_financing.invoices.add(model.invoice)

    Command().handle(dry_run=False, email=None, plan_financing_id=None)

    model.plan_financing.refresh_from_db()
    assert model.plan_financing.created_by_admin is False
    patch_charge.assert_not_called()


def test_email_filter_skips_other_users(database: capy.Database, patch_charge):
    model = _create_plan_with_proof(database, email="staff@example.com")

    Command().handle(dry_run=False, email="other@example.com", plan_financing_id=None)

    model.plan_financing.refresh_from_db()
    assert model.plan_financing.created_by_admin is False
    patch_charge.assert_not_called()


def test_marks_expired_plan_but_does_not_charge(database: capy.Database, patch_charge):
    model = _create_plan_with_proof(database, status=PlanFinancing.Status.EXPIRED)

    Command().handle(dry_run=False, email=None, plan_financing_id=None)

    model.plan_financing.refresh_from_db()
    assert model.plan_financing.created_by_admin is True
    patch_charge.assert_not_called()


def test_marks_payment_issue_and_queues_overdue_charge(database: capy.Database, patch_charge):
    model = _create_plan_with_proof(database, status=PlanFinancing.Status.PAYMENT_ISSUE)

    Command().handle(dry_run=False, email=None, plan_financing_id=None)

    model.plan_financing.refresh_from_db()
    assert model.plan_financing.created_by_admin is True
    patch_charge.assert_called_once_with(model.plan_financing.id)
