from unittest.mock import MagicMock

import capyc.pytest as capy
import pytest
from dateutil.relativedelta import relativedelta
from django.utils import timezone

from breathecode.payments import tasks
from breathecode.payments.management.commands.retry_overdue_staff_auto_charges import Command
from breathecode.payments.models import Bag, Invoice

UTC_NOW = timezone.now()

pytestmark = pytest.mark.usefixtures("db")


@pytest.fixture(autouse=True)
def patch_charge(monkeypatch: pytest.MonkeyPatch):
    delay = MagicMock()
    monkeypatch.setattr(tasks.charge_plan_financing, "delay", delay)
    monkeypatch.setattr("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    return delay


def _add_stripe_invoice(plan_financing, template_invoice, paid_at):
    bag = Bag(
        user=template_invoice.user,
        academy=template_invoice.academy,
        currency=template_invoice.currency,
        status="PAID",
        type="CHARGE",
        was_delivered=True,
        how_many_installments=plan_financing.how_many_installments,
        is_recurrent=True,
    )
    bag.save()
    invoice = Invoice(
        user=template_invoice.user,
        academy=template_invoice.academy,
        currency=template_invoice.currency,
        bag=bag,
        amount=template_invoice.amount,
        paid_at=paid_at,
        status="FULFILLED",
        stripe_id="ch_auto",
    )
    invoice.save()
    plan_financing.invoices.add(invoice)
    return invoice


def _create_overdue_staff_auto_charge(database: capy.Database, email="mel_oubi@hotmail.com"):
    model = database.create(
        academy=1,
        user={"email": email},
        proof_of_payment=1,
        plan={"is_renewable": False},
        plan_financing={
            "valid_until": UTC_NOW + relativedelta(months=6),
            "next_payment_at": UTC_NOW - relativedelta(days=9),
            "monthly_price": 100.0,
            "how_many_installments": 12,
            "installments_paid": 2,
            "plan_expires_at": UTC_NOW + relativedelta(months=12),
            "status": "ACTIVE",
            "user_id": 1,
            "created_by_admin": True,
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
    _add_stripe_invoice(model.plan_financing, model.invoice, UTC_NOW - relativedelta(months=1))
    return model


def test_queues_overdue_staff_plan_with_previous_auto_charge(database: capy.Database, patch_charge):
    model = _create_overdue_staff_auto_charge(database)

    Command().handle(dry_run=False, email=None, plan_financing_id=None)

    patch_charge.assert_called_once_with(model.plan_financing.id)


def test_dry_run_does_not_queue(database: capy.Database, patch_charge):
    _create_overdue_staff_auto_charge(database)

    Command().handle(dry_run=True, email=None, plan_financing_id=None)

    patch_charge.assert_not_called()


def test_email_filter_skips_other_users(database: capy.Database, patch_charge):
    _create_overdue_staff_auto_charge(database, email="mel_oubi@hotmail.com")

    Command().handle(dry_run=False, email="other@example.com", plan_financing_id=None)

    patch_charge.assert_not_called()


def test_queues_overdue_admin_plan_without_stripe_history(database: capy.Database, patch_charge):
    model = database.create(
        academy=1,
        proof_of_payment=1,
        plan={"is_renewable": False},
        plan_financing={
            "valid_until": UTC_NOW + relativedelta(months=6),
            "next_payment_at": UTC_NOW - relativedelta(days=9),
            "monthly_price": 100.0,
            "how_many_installments": 3,
            "installments_paid": 1,
            "plan_expires_at": UTC_NOW + relativedelta(months=12),
            "status": "ACTIVE",
            "created_by_admin": True,
        },
        bag={"how_many_installments": 3, "was_delivered": True, "type": "BAG"},
        invoice={
            "paid_at": UTC_NOW - relativedelta(months=2),
            "amount": 100.0,
            "status": "FULFILLED",
            "proof_id": 1,
            "stripe_id": None,
        },
    )
    model.plan_financing.invoices.add(model.invoice)

    Command().handle(dry_run=False, email=None, plan_financing_id=None)

    patch_charge.assert_called_once_with(model.plan_financing.id)
