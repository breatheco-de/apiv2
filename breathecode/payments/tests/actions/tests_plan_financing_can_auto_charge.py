import pytest
from dateutil.relativedelta import relativedelta
from django.utils import timezone

from breathecode.payments.actions import plan_financing_can_auto_charge
from breathecode.payments.models import Bag, Invoice, PaymentMethod
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode

UTC_NOW = timezone.now()

pytestmark = pytest.mark.django_db


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


def test_staff_assigned_uses_oldest_invoice_even_if_later_charge_has_no_proof(bc: Breathecode):
    model = bc.database.create(
        proof_of_payment=1,
        plan={"is_renewable": False, "time_of_life": 1, "time_of_life_unit": "MONTH"},
        plan_financing={
            "valid_until": UTC_NOW + relativedelta(months=6),
            "next_payment_at": UTC_NOW - relativedelta(days=5),
            "monthly_price": 100.0,
            "how_many_installments": 12,
            "installments_paid": 2,
            "plan_expires_at": UTC_NOW + relativedelta(months=12),
            "status": "ACTIVE",
            "created_by_admin": True,
        },
        bag={"how_many_installments": 12, "was_delivered": True, "type": "BAG"},
        invoice={
            "paid_at": UTC_NOW - relativedelta(months=2),
            "amount": 100.0,
            "status": "FULFILLED",
            "stripe_id": None,
        },
    )
    model.invoice.proof = model.proof_of_payment
    model.invoice.save()
    model.plan_financing.invoices.add(model.invoice)
    _add_stripe_invoice(model.plan_financing, model.invoice, UTC_NOW - relativedelta(months=1))

    assert plan_financing_can_auto_charge(model.plan_financing) is True


def test_staff_assigned_without_stripe_history_cannot_auto_charge(bc: Breathecode):
    model = bc.database.create(
        proof_of_payment=1,
        plan={"is_renewable": False, "time_of_life": 1, "time_of_life_unit": "MONTH"},
        plan_financing={
            "valid_until": UTC_NOW + relativedelta(months=6),
            "next_payment_at": UTC_NOW - relativedelta(days=5),
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
            "stripe_id": None,
        },
    )
    model.invoice.proof = model.proof_of_payment
    model.invoice.save()
    model.plan_financing.invoices.add(model.invoice)

    assert plan_financing_can_auto_charge(model.plan_financing) is False


def test_credit_card_staff_invoice_can_auto_charge_without_stripe_history(bc: Breathecode):
    model = bc.database.create(
        proof_of_payment=1,
        plan={"is_renewable": False, "time_of_life": 1, "time_of_life_unit": "MONTH"},
        plan_financing={
            "valid_until": UTC_NOW + relativedelta(months=6),
            "next_payment_at": UTC_NOW - relativedelta(days=5),
            "monthly_price": 100.0,
            "how_many_installments": 3,
            "installments_paid": 1,
            "plan_expires_at": UTC_NOW + relativedelta(months=12),
            "externally_managed": False,
            "status": "ACTIVE",
            "created_by_admin": True,
        },
        bag={"how_many_installments": 3, "was_delivered": True, "type": "BAG"},
        invoice={
            "paid_at": UTC_NOW - relativedelta(months=2),
            "amount": 100.0,
            "status": "FULFILLED",
            "stripe_id": None,
            "externally_managed": False,
        },
    )
    payment_method = PaymentMethod.objects.create(
        academy=model.academy,
        currency=model.currency,
        title="Card",
        description="Card",
        lang="en-US",
        is_credit_card=True,
        is_crypto=False,
    )
    model.invoice.payment_method = payment_method
    model.invoice.externally_managed = True
    model.invoice.proof = model.proof_of_payment
    model.invoice.save()
    model.plan_financing.invoices.add(model.invoice)

    assert plan_financing_can_auto_charge(model.plan_financing) is True


def test_created_by_admin_flag_is_staff_without_proof(bc: Breathecode):
    model = bc.database.create(
        plan={"is_renewable": False, "time_of_life": 1, "time_of_life_unit": "MONTH"},
        plan_financing={
            "valid_until": UTC_NOW + relativedelta(months=6),
            "next_payment_at": UTC_NOW - relativedelta(days=5),
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
            "proof_id": None,
            "stripe_id": "ch_card",
        },
    )
    model.plan_financing.invoices.add(model.invoice)

    assert plan_financing_can_auto_charge(model.plan_financing) is True


def _staff_plan_financing_kwargs():
    return {
        "valid_until": UTC_NOW + relativedelta(months=6),
        "next_payment_at": UTC_NOW - relativedelta(days=5),
        "monthly_price": 100.0,
        "how_many_installments": 3,
        "installments_paid": 1,
        "plan_expires_at": UTC_NOW + relativedelta(months=12),
        "status": "ACTIVE",
        "created_by_admin": True,
        "externally_managed": False,
    }


def test_klarna_checkout_invoice_cannot_auto_charge_even_with_stripe_id(bc: Breathecode):
    model = bc.database.create(
        plan={"is_renewable": False, "time_of_life": 1, "time_of_life_unit": "MONTH"},
        plan_financing=_staff_plan_financing_kwargs(),
        bag={"how_many_installments": 3, "was_delivered": True, "type": "BAG"},
        invoice={
            "paid_at": UTC_NOW - relativedelta(months=2),
            "amount": 100.0,
            "status": "FULFILLED",
            "proof_id": None,
            "stripe_id": "cs_test_klarna",
            "externally_managed": False,
        },
    )
    payment_method = PaymentMethod.objects.create(
        academy=model.academy,
        currency=model.currency,
        title="Klarna",
        description="Klarna",
        lang="en-US",
        is_credit_card=False,
        is_crypto=False,
        provider_settings={"stripe_payment_method_types": ["klarna"]},
        is_financing_managed_by_provider=False,
    )
    model.invoice.payment_method = payment_method
    model.invoice.externally_managed = True
    model.invoice.save()
    model.plan_financing.invoices.add(model.invoice)

    assert plan_financing_can_auto_charge(model.plan_financing) is False


def test_affirm_bnpl_cannot_auto_charge(bc: Breathecode):
    model = bc.database.create(
        plan={"is_renewable": False, "time_of_life": 1, "time_of_life_unit": "MONTH"},
        plan_financing=_staff_plan_financing_kwargs(),
        bag={"how_many_installments": 3, "was_delivered": True, "type": "BAG"},
        invoice={
            "paid_at": UTC_NOW - relativedelta(months=2),
            "amount": 300.0,
            "status": "FULFILLED",
            "proof_id": None,
            "stripe_id": "cs_test_affirm",
            "externally_managed": False,
        },
    )
    payment_method = PaymentMethod.objects.create(
        academy=model.academy,
        currency=model.currency,
        title="Affirm",
        description="Affirm",
        lang="en-US",
        is_credit_card=False,
        is_crypto=False,
        provider_settings={"stripe_payment_method_types": ["affirm"]},
        is_financing_managed_by_provider=True,
    )
    model.invoice.payment_method = payment_method
    model.invoice.externally_managed = True
    model.invoice.save()
    model.plan_financing.invoices.add(model.invoice)

    assert plan_financing_can_auto_charge(model.plan_financing) is False
