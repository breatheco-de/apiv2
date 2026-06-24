from unittest.mock import MagicMock, call, patch

import pytest
from django.utils import timezone

from breathecode.monitoring import signals as monitoring_signals
from breathecode.payments.models import Invoice, PaymentMethod
from breathecode.payments import tasks
from breathecode.tests.mixins.breathecode_mixin import Breathecode

UTC_NOW = timezone.now()


pytestmark = pytest.mark.django_db(reset_sequences=True)


def _stripe_event_payload(metadata, *, event_type="checkout.session.completed", session_id="cs_test_123", payment_status="paid"):
    return {
        "type": event_type,
        "data": {
            "object": {
                "id": session_id,
                "payment_status": payment_status,
                "metadata": metadata,
            }
        },
    }


def _checkout_metadata(model, payment_method, **overrides):
    data = {
        "bag_id": str(model.bag.id),
        "user_id": str(model.user.id),
        "payment_method_id": str(payment_method.id),
        "amount": "100.0",
        "original_price": "100.0",
        "chosen_period": "YEAR",
        "how_many_installments": "0",
        "selected_cohort": "",
        "user_email": model.user.email,
    }
    data.update(overrides)
    return data


@pytest.fixture
def setup_mocks(monkeypatch):
    monkeypatch.setattr(tasks.build_subscription, "delay", MagicMock())
    monkeypatch.setattr(tasks.build_plan_financing, "delay", MagicMock())
    monkeypatch.setattr(tasks.build_free_subscription, "delay", MagicMock())
    monkeypatch.setattr("breathecode.activity.tasks.add_activity.delay", MagicMock())
    monkeypatch.setattr("breathecode.commission.tasks.register_referral_from_invoice.delay", MagicMock())
    monkeypatch.setattr("breathecode.payments.actions.grant_student_capabilities", MagicMock())
    monkeypatch.setattr("breathecode.payments.actions.create_seller_reward_coupons", MagicMock())
    monkeypatch.setattr("breathecode.payments.actions.build_plan_addons_financings", MagicMock())


def test__stripe_checkout__without_bag_id__does_nothing(bc: Breathecode, enable_signals, setup_mocks):
    enable_signals()

    stripe_event = _stripe_event_payload({})
    model = bc.database.create(stripe_event=stripe_event)

    monitoring_signals.stripe_webhook.send(instance=model.stripe_event, sender=model.stripe_event.__class__)

    assert bc.database.list_of("payments.Invoice") == []
    assert bc.database.list_of("monitoring.StripeEvent") == [
        {
            **bc.format.to_dict(model.stripe_event),
            "status": "PENDING",
            "status_texts": {},
        }
    ]


def test__stripe_checkout__unpaid_session__marks_handler_done(bc: Breathecode, enable_signals, setup_mocks):
    enable_signals()

    model = bc.database.create(
        user=1,
        bag={"status": "CHECKING", "token": "abc"},
        academy=1,
        currency=1,
        plan=1,
    )
    payment_method = PaymentMethod.objects.create(
        academy=model.academy,
        title="Klarna",
        description="Klarna",
        lang="en-US",
        provider_settings={"stripe_payment_method_types": ["klarna"]},
    )
    metadata = _checkout_metadata(model, payment_method)
    stripe_event = _stripe_event_payload(metadata, payment_status="unpaid")
    event_model = bc.database.create(stripe_event=stripe_event)

    monitoring_signals.stripe_webhook.send(instance=event_model.stripe_event, sender=event_model.stripe_event.__class__)

    assert bc.database.list_of("payments.Invoice") == []
    assert bc.database.get("payments.Bag", model.bag.id, dict=True)["status"] == "CHECKING"
    assert bc.database.get("monitoring.StripeEvent", event_model.stripe_event.id, dict=True)["status"] == "DONE"


@patch("breathecode.payments.actions.calculate_invoice_breakdown", MagicMock(return_value={}))
def test__stripe_checkout__creates_invoice_and_fulfills_subscription(
    mock_breakdown, bc: Breathecode, enable_signals, setup_mocks
):
    enable_signals()

    model = bc.database.create(
        user=1,
        bag={"status": "CHECKING", "token": "abc", "chosen_period": "NO_SET"},
        academy=1,
        currency=1,
        plan=1,
    )
    payment_method = PaymentMethod.objects.create(
        academy=model.academy,
        title="Klarna",
        description="Klarna",
        lang="en-US",
        provider_settings={"stripe_payment_method_types": ["klarna"]},
    )
    metadata = _checkout_metadata(model, payment_method)
    stripe_event = _stripe_event_payload(metadata, session_id="cs_fulfill_1")
    event_model = bc.database.create(stripe_event=stripe_event)

    monitoring_signals.stripe_webhook.send(instance=event_model.stripe_event, sender=event_model.stripe_event.__class__)

    assert tasks.build_subscription.delay.call_args_list == [
        call(model.bag.id, 1, conversion_info="", externally_managed=True),
    ]
    assert tasks.build_plan_financing.delay.call_args_list == []

    invoice = bc.database.get("payments.Invoice", 1, dict=True)
    assert invoice["stripe_id"] == "cs_fulfill_1"
    assert invoice["status"] == Invoice.Status.FULFILLED
    assert invoice["externally_managed"] is True
    assert invoice["payment_method_id"] == payment_method.id

    bag = bc.database.get("payments.Bag", model.bag.id, dict=True)
    assert bag["status"] == "PAID"
    assert bag["token"] is None


@patch("breathecode.payments.actions.calculate_invoice_breakdown", MagicMock(return_value={}))
def test__stripe_checkout__idempotent_on_duplicate_event(
    mock_breakdown, bc: Breathecode, enable_signals, setup_mocks
):
    enable_signals()

    model = bc.database.create(
        user=1,
        bag={"status": "CHECKING", "token": "abc"},
        academy=1,
        currency=1,
        plan=1,
    )
    payment_method = PaymentMethod.objects.create(
        academy=model.academy,
        title="Klarna",
        description="Klarna",
        lang="en-US",
        provider_settings={"stripe_payment_method_types": ["klarna"]},
    )
    metadata = _checkout_metadata(model, payment_method)
    stripe_event = _stripe_event_payload(metadata, session_id="cs_idempotent")
    event_model = bc.database.create(stripe_event=stripe_event)

    monitoring_signals.stripe_webhook.send(instance=event_model.stripe_event, sender=event_model.stripe_event.__class__)
    monitoring_signals.stripe_webhook.send(instance=event_model.stripe_event, sender=event_model.stripe_event.__class__)

    assert len(bc.database.list_of("payments.Invoice")) == 1
    assert tasks.build_subscription.delay.call_count == 1


@patch("breathecode.payments.actions.calculate_invoice_breakdown", MagicMock(return_value={}))
def test__stripe_checkout__plan_financing_path(
    mock_breakdown, bc: Breathecode, enable_signals, setup_mocks
):
    enable_signals()

    model = bc.database.create(
        user=1,
        bag={
            "status": "CHECKING",
            "token": "abc",
            "how_many_installments": 6,
        },
        academy=1,
        currency=1,
        plan=1,
    )
    payment_method = PaymentMethod.objects.create(
        academy=model.academy,
        title="Klarna",
        description="Klarna",
        lang="en-US",
        provider_settings={"stripe_payment_method_types": ["klarna"]},
        is_financing_managed_by_provider=True,
    )
    metadata = _checkout_metadata(model, payment_method, how_many_installments="6", amount="600.0")
    stripe_event = _stripe_event_payload(metadata, session_id="cs_pf_1")
    event_model = bc.database.create(stripe_event=stripe_event)

    monitoring_signals.stripe_webhook.send(instance=event_model.stripe_event, sender=event_model.stripe_event.__class__)

    assert tasks.build_plan_financing.delay.call_args_list == [
        call(model.bag.id, 1, conversion_info="", externally_managed=True),
    ]
    assert tasks.build_subscription.delay.call_args_list == []


@patch("breathecode.payments.actions.calculate_invoice_breakdown", MagicMock(return_value={}))
def test__stripe_checkout__async_payment_succeeded__fulfills_subscription(
    mock_breakdown, bc: Breathecode, enable_signals, setup_mocks
):
    enable_signals()

    model = bc.database.create(
        user=1,
        bag={"status": "CHECKING", "token": "abc", "chosen_period": "NO_SET"},
        academy=1,
        currency=1,
        plan=1,
    )
    payment_method = PaymentMethod.objects.create(
        academy=model.academy,
        title="Klarna",
        description="Klarna",
        lang="en-US",
        provider_settings={"stripe_payment_method_types": ["klarna"]},
    )
    metadata = _checkout_metadata(model, payment_method)
    stripe_event = _stripe_event_payload(
        metadata,
        event_type="checkout.session.async_payment_succeeded",
        session_id="cs_async_paid",
        payment_status="paid",
    )
    event_model = bc.database.create(stripe_event=stripe_event)

    monitoring_signals.stripe_webhook.send(instance=event_model.stripe_event, sender=event_model.stripe_event.__class__)

    assert tasks.build_subscription.delay.call_args_list == [
        call(model.bag.id, 1, conversion_info="", externally_managed=True),
    ]
    assert bc.database.get("payments.Bag", model.bag.id, dict=True)["status"] == "PAID"


def test__stripe_checkout__async_payment_failed__marks_handler_error(bc: Breathecode, enable_signals, setup_mocks):
    enable_signals()

    model = bc.database.create(
        user=1,
        bag={"status": "CHECKING", "token": "abc"},
        academy=1,
        currency=1,
        plan=1,
    )
    payment_method = PaymentMethod.objects.create(
        academy=model.academy,
        title="Klarna",
        description="Klarna",
        lang="en-US",
        provider_settings={"stripe_payment_method_types": ["klarna"]},
    )
    metadata = _checkout_metadata(model, payment_method)
    stripe_event = _stripe_event_payload(
        metadata,
        event_type="checkout.session.async_payment_failed",
        session_id="cs_async_failed",
        payment_status="unpaid",
    )
    event_model = bc.database.create(stripe_event=stripe_event)

    monitoring_signals.stripe_webhook.send(instance=event_model.stripe_event, sender=event_model.stripe_event.__class__)

    assert bc.database.list_of("payments.Invoice") == []
    assert bc.database.get("payments.Bag", model.bag.id, dict=True)["status"] == "CHECKING"
    event = bc.database.get("monitoring.StripeEvent", event_model.stripe_event.id, dict=True)
    assert event["status"] == "ERROR"
    assert event["status_texts"]["payments.stripe_checkout_payment_fulfillment"] == "async payment failed"


def test__stripe_checkout__subscription_id_in_metadata__skips_purchase_fulfillment(
    bc: Breathecode, enable_signals, setup_mocks
):
    enable_signals()

    model = bc.database.create(
        user=1,
        bag={"status": "CHECKING", "token": "abc", "chosen_period": "NO_SET"},
        academy=1,
        currency=1,
        plan=1,
        subscription={"status": "ACTIVE"},
    )
    payment_method = PaymentMethod.objects.create(
        academy=model.academy,
        title="Klarna",
        description="Klarna",
        lang="en-US",
        provider_settings={"stripe_payment_method_types": ["klarna"]},
    )
    metadata = _checkout_metadata(model, payment_method, subscription_id=str(model.subscription.id))
    stripe_event = _stripe_event_payload(metadata, session_id="cs_renew_skip_purchase")
    event_model = bc.database.create(stripe_event=stripe_event)

    monitoring_signals.stripe_webhook.send(instance=event_model.stripe_event, sender=event_model.stripe_event.__class__)

    assert tasks.build_subscription.delay.call_args_list == []
    assert bc.database.list_of("payments.Invoice") == []
