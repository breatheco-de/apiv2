from unittest.mock import MagicMock, patch

import capyc.pytest as capy
import pytest
from dateutil.relativedelta import relativedelta
from django.utils import timezone

from breathecode.notify import actions as notify_actions
from breathecode.payments.models import Bag, Invoice
from breathecode.payments.tasks import charge_plan_financing

UTC_NOW = timezone.now()

pytestmark = pytest.mark.usefixtures("db")


def fake_stripe_pay(**kwargs):
    def wrapper(user, bag, amount: int, currency="usd", description="", **extra_kwargs):
        filtered_kwargs = {k: v for k, v in kwargs.items() if k not in ["user", "bag", "academy", "currency", "amount"]}
        invoice = Invoice(
            user=user, bag=bag, academy=bag.academy, currency=bag.currency, amount=amount, **filtered_kwargs
        )
        invoice.save()
        return invoice

    return wrapper


@patch("logging.Logger.info", MagicMock())
@patch("logging.Logger.error", MagicMock())
@patch("breathecode.notify.actions.send_email_message", MagicMock())
@patch("breathecode.payments.tasks.renew_plan_financing_consumables.delay", MagicMock())
@patch("mixer.main.LOGGER.info", MagicMock())
@patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
def test_staff_assigned_with_previous_stripe_invoice_auto_charges(database: capy.Database):
    model = database.create(
        academy=1,
        proof_of_payment=1,
        plan={"is_renewable": False},
        plan_financing={
            "valid_until": UTC_NOW + relativedelta(months=6),
            "next_payment_at": UTC_NOW - relativedelta(days=9),
            "monthly_price": 100.0,
            "how_many_installments": 12,
            "installments_paid": 2,
            "plan_expires_at": UTC_NOW + relativedelta(months=12),
            "externally_managed": False,
            "status": "ACTIVE",
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
    model.plan_financing.plans.add(model.plan)
    model.plan_financing.invoices.add(model.invoice)

    stripe_bag = Bag(
        user=model.invoice.user,
        academy=model.invoice.academy,
        currency=model.invoice.currency,
        status="PAID",
        type="CHARGE",
        was_delivered=True,
        how_many_installments=12,
        is_recurrent=True,
    )
    stripe_bag.save()
    stripe_invoice = Invoice(
        user=model.invoice.user,
        academy=model.invoice.academy,
        currency=model.invoice.currency,
        bag=stripe_bag,
        amount=100.0,
        paid_at=UTC_NOW - relativedelta(months=1),
        status="FULFILLED",
        stripe_id="ch_auto",
    )
    stripe_invoice.save()
    model.plan_financing.invoices.add(stripe_invoice)

    with patch(
        "breathecode.payments.services.stripe.Stripe.pay",
        MagicMock(side_effect=fake_stripe_pay(paid_at=UTC_NOW, status="FULFILLED")),
    ) as mock_stripe_pay:
        charge_plan_financing.delay(1)

    mock_stripe_pay.assert_called_once()
    pf = database.list_of("payments.PlanFinancing")[0]
    assert pf["status"] == "ACTIVE"
    assert pf["installments_paid"] == 3
    assert pf["next_payment_at"] == model.plan_financing.next_payment_at + relativedelta(months=1)
    assert len(database.list_of("payments.Invoice")) == 3
    assert notify_actions.send_email_message.call_count == 1
