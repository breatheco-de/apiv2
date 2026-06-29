"""Tests for supervise_stripe_checkout_events_in_error and its issue handler."""

import json
from datetime import timedelta
from unittest.mock import MagicMock, call, patch

import pytest
from django.utils import timezone

from breathecode.monitoring.models import Supervisor as SupervisorModel, SupervisorIssue, StripeEvent
from breathecode.payments import actions, tasks
from breathecode.payments.models import Invoice, PaymentMethod
from breathecode.payments.supervisors import (
    stripe_checkout_fulfillment_error,
    supervise_stripe_checkout_events_in_error,
)
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode

UTC_NOW = timezone.now()

pytestmark = pytest.mark.django_db(reset_sequences=True)


class Supervisor:

    def __init__(self, bc: Breathecode):
        self._bc = bc

    def list(self):
        supervisors = SupervisorModel.objects.all()
        return [
            {
                "task_module": supervisor.task_module,
                "task_name": supervisor.task_name,
            }
            for supervisor in supervisors
        ]

    def log(self, module, name):
        issues = SupervisorIssue.objects.filter(supervisor__task_module=module, supervisor__task_name=name)
        return [x.error for x in issues]


def _checkout_event_data(
    *,
    bag_id: int,
    session_id: str = "cs_test_checkout",
    payment_status: str = "paid",
    success_url: str | None = None,
    **metadata,
):
    obj = {
        "id": session_id,
        "payment_status": payment_status,
        "metadata": {
            "bag_id": str(bag_id),
            **metadata,
        },
    }
    if success_url:
        obj["success_url"] = success_url
    return {
        "type": "checkout.session.completed",
        "data": {
            "object": obj,
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
        "fulfillment_snapshot": json.dumps(
            {
                "plan_ids": list(model.bag.plans.values_list("id", flat=True)),
                "plan_addon_ids": list(model.bag.plan_addons.values_list("id", flat=True)),
                "coupon_ids": list(model.bag.coupons.values_list("id", flat=True)),
            },
            separators=(",", ":"),
        ),
    }
    data.update(overrides)
    return data


@pytest.fixture
def setup_mocks(monkeypatch):
    monkeypatch.setattr(tasks.build_subscription, "delay", MagicMock())
    monkeypatch.setattr(tasks.build_plan_financing, "delay", MagicMock())
    monkeypatch.setattr(tasks.build_free_subscription, "delay", MagicMock())
    monkeypatch.setattr(tasks.charge_subscription, "delay", MagicMock())
    monkeypatch.setattr(tasks.charge_plan_financing, "delay", MagicMock())
    monkeypatch.setattr("breathecode.activity.tasks.add_activity.delay", MagicMock())
    monkeypatch.setattr("breathecode.commission.tasks.register_referral_from_invoice.delay", MagicMock())
    monkeypatch.setattr("breathecode.payments.actions.grant_student_capabilities", MagicMock())
    monkeypatch.setattr("breathecode.payments.actions.create_seller_reward_coupons", MagicMock())
    monkeypatch.setattr("breathecode.payments.actions.build_plan_addons_financings", MagicMock())


def test_supervise_stripe_checkout_events_in_error__detects_failed_checkout(database, bc: Breathecode):
    model = database.create(user=1, academy=1, bag={"status": "CHECKING"})
    StripeEvent.objects.create(
        stripe_id="cs_failed_checkout",
        type="checkout.session.completed",
        status="ERROR",
        status_texts={"payments.stripe_checkout_payment_fulfillment": "bag not found"},
        data=_checkout_event_data(bag_id=model.bag.id, session_id="cs_failed_checkout")["data"],
        created_at=UTC_NOW - timedelta(minutes=10),
    )

    supervise_stripe_checkout_events_in_error()

    supervisor = Supervisor(bc)
    assert supervisor.list() == [
        {
            "task_module": "breathecode.payments.supervisors",
            "task_name": "supervise_stripe_checkout_events_in_error",
        },
    ]
    assert len(supervisor.log("breathecode.payments.supervisors", "supervise_stripe_checkout_events_in_error")) == 1

    issue = SupervisorIssue.objects.get()
    assert issue.code == "stripe-checkout-fulfillment-error"
    assert issue.params["bag_id"] == model.bag.id
    assert "stripe_event_id" in issue.params


def test_supervise_stripe_checkout_events_in_error__skips_unverified_signature(database, bc: Breathecode):
    model = database.create(user=1, academy=1, bag={"status": "CHECKING"})
    StripeEvent.objects.create(
        stripe_id="cs_unverified",
        type="checkout.session.completed",
        status="ERROR",
        status_texts={"verified": False, "slug": "not-allowed"},
        data=_checkout_event_data(bag_id=model.bag.id, session_id="cs_unverified")["data"],
        created_at=UTC_NOW - timedelta(minutes=10),
    )

    supervise_stripe_checkout_events_in_error()

    assert SupervisorIssue.objects.count() == 0


def test_supervise_stripe_checkout_events_in_error__skips_when_invoice_already_fulfilled(database, bc: Breathecode):
    model = database.create(user=1, academy=1, bag={"status": "PAID", "was_delivered": True})
    Invoice.objects.create(
        user=model.user,
        academy=model.academy,
        bag=model.bag,
        currency=model.currency,
        amount=100.0,
        status=Invoice.Status.FULFILLED,
        stripe_id="cs_already_fulfilled",
        paid_at=UTC_NOW - timedelta(minutes=15),
    )
    StripeEvent.objects.create(
        stripe_id="cs_already_fulfilled",
        type="checkout.session.completed",
        status="ERROR",
        status_texts={"payments.stripe_checkout_payment_fulfillment": "transient error"},
        data=_checkout_event_data(bag_id=model.bag.id, session_id="cs_already_fulfilled")["data"],
        created_at=UTC_NOW - timedelta(minutes=10),
    )

    supervise_stripe_checkout_events_in_error()

    assert SupervisorIssue.objects.count() == 0


def test_supervise_stripe_checkout_events_in_error__skips_pending_bag_delivery_case(database, bc: Breathecode):
    model = database.create(user=1, academy=1, bag={"status": "PAID", "was_delivered": False})
    Invoice.objects.create(
        user=model.user,
        academy=model.academy,
        bag=model.bag,
        currency=model.currency,
        amount=100.0,
        status=Invoice.Status.FULFILLED,
        stripe_id="cs_pending_build",
        paid_at=UTC_NOW - timedelta(minutes=15),
    )
    StripeEvent.objects.create(
        stripe_id="cs_pending_build",
        type="checkout.session.completed",
        status="ERROR",
        status_texts={"payments.stripe_checkout_payment_fulfillment": "build failed"},
        data=_checkout_event_data(bag_id=model.bag.id, session_id="cs_pending_build")["data"],
        created_at=UTC_NOW - timedelta(minutes=10),
    )

    supervise_stripe_checkout_events_in_error()

    assert SupervisorIssue.objects.count() == 0


def test_supervise_stripe_checkout_events_in_error__detects_when_bag_paid_by_other_session(database, bc: Breathecode):
    model = database.create(user=1, academy=1, bag={"status": "PAID", "was_delivered": True})
    Invoice.objects.create(
        user=model.user,
        academy=model.academy,
        bag=model.bag,
        currency=model.currency,
        amount=100.0,
        status=Invoice.Status.FULFILLED,
        stripe_id="cs_other_session",
        paid_at=UTC_NOW - timedelta(minutes=15),
    )
    StripeEvent.objects.create(
        stripe_id="cs_stale_failed",
        type="checkout.session.completed",
        status="ERROR",
        status_texts={"payments.stripe_checkout_payment_fulfillment": "transient error"},
        data=_checkout_event_data(bag_id=model.bag.id, session_id="cs_stale_failed")["data"],
        created_at=UTC_NOW - timedelta(minutes=10),
    )

    supervise_stripe_checkout_events_in_error()

    assert SupervisorIssue.objects.filter(code="stripe-checkout-fulfillment-error").count() == 1


def test_supervise_stripe_checkout_events_in_error__skips_unpaid_session(database, bc: Breathecode):
    model = database.create(user=1, academy=1, bag={"status": "CHECKING"})
    StripeEvent.objects.create(
        stripe_id="cs_unpaid",
        type="checkout.session.completed",
        status="ERROR",
        status_texts={"payments.stripe_checkout_payment_fulfillment": "async payment failed"},
        data=_checkout_event_data(bag_id=model.bag.id, session_id="cs_unpaid", payment_status="unpaid")["data"],
        created_at=UTC_NOW - timedelta(minutes=10),
    )

    supervise_stripe_checkout_events_in_error()

    assert SupervisorIssue.objects.count() == 0


@patch("breathecode.notify.actions.send_email_message", MagicMock())
@patch("breathecode.payments.actions.calculate_invoice_breakdown", MagicMock(return_value={}))
def test_stripe_checkout_fulfillment_error__replays_webhook_and_fixes(
    mock_breakdown, mock_send_email, database, bc: Breathecode, enable_signals, setup_mocks
):
    enable_signals()

    model = database.create(
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
    stripe_event = StripeEvent.objects.create(
        stripe_id="evt_retry_checkout",
        type="checkout.session.completed",
        status="ERROR",
        status_texts={"payments.stripe_checkout_payment_fulfillment": "transient error"},
        data=_checkout_event_data(bag_id=model.bag.id, session_id="cs_retry_checkout", **metadata)["data"],
        created_at=UTC_NOW - timedelta(minutes=10),
    )

    supervise_stripe_checkout_events_in_error()
    issue = SupervisorIssue.objects.get()

    result = stripe_checkout_fulfillment_error(issue.id)

    assert result is True
    issue.refresh_from_db()
    assert issue.fixed is True
    stripe_event.refresh_from_db()
    assert stripe_event.status == "DONE"
    assert bc.database.get("payments.Bag", model.bag.id, dict=True)["status"] == "PAID"
    assert tasks.build_subscription.delay.call_args_list == [
        call(model.bag.id, 1, conversion_info="", externally_managed=True),
    ]
    assert mock_send_email.call_count == 1


@patch("breathecode.payments.actions.calculate_invoice_breakdown", MagicMock(return_value={}))
def test_stripe_checkout_fulfillment_error__injects_selected_cohort_from_success_url(
    mock_breakdown, database, bc: Breathecode, enable_signals, setup_mocks
):
    enable_signals()

    model = database.create(
        user=1,
        bag={"status": "CHECKING", "token": "abc", "chosen_period": "NO_SET"},
        academy=1,
        currency=1,
        plan=1,
        cohort={"slug": "test-plan-cohort"},
    )
    payment_method = PaymentMethod.objects.create(
        academy=model.academy,
        title="Klarna",
        description="Klarna",
        lang="en-US",
        provider_settings={"stripe_payment_method_types": ["klarna"]},
    )
    metadata = _checkout_metadata(model, payment_method, selected_cohort="")
    stripe_event = StripeEvent.objects.create(
        stripe_id="evt_cohort_from_url",
        type="checkout.session.completed",
        status="ERROR",
        status_texts={"payments.stripe_checkout_payment_fulfillment": "transient error"},
        data=_checkout_event_data(
            bag_id=model.bag.id,
            session_id="cs_cohort_from_url",
            success_url=f"http://localhost:3001/payment-success?plan=test-plan&cohort={model.cohort.id}",
            **metadata,
        )["data"],
        created_at=UTC_NOW - timedelta(minutes=10),
    )

    supervise_stripe_checkout_events_in_error()
    issue = SupervisorIssue.objects.get()

    result = stripe_checkout_fulfillment_error(issue.id)

    assert result is True
    stripe_event.refresh_from_db()
    assert stripe_event.data["object"]["metadata"]["selected_cohort"] == model.cohort.slug
    grant_mock = actions.grant_student_capabilities
    assert len(grant_mock.call_args_list) == 1
    assert grant_mock.call_args_list[0].kwargs["selected_cohort"] == model.cohort.slug


def test_stripe_checkout_fulfillment_error__returns_true_when_already_fulfilled(database, bc: Breathecode):
    model = database.create(user=1, academy=1, bag={"status": "PAID", "was_delivered": True})
    Invoice.objects.create(
        user=model.user,
        academy=model.academy,
        bag=model.bag,
        currency=model.currency,
        amount=100.0,
        status=Invoice.Status.FULFILLED,
        stripe_id="cs_already_done",
        paid_at=UTC_NOW - timedelta(minutes=15),
    )
    stripe_event = StripeEvent.objects.create(
        stripe_id="evt_already_done",
        type="checkout.session.completed",
        status="ERROR",
        status_texts={"payments.stripe_checkout_payment_fulfillment": "old error"},
        data=_checkout_event_data(bag_id=model.bag.id, session_id="cs_already_done")["data"],
        created_at=UTC_NOW - timedelta(minutes=10),
    )

    supervise_stripe_checkout_events_in_error()
    supervisor = SupervisorModel.objects.get(task_name="supervise_stripe_checkout_events_in_error")
    issue = SupervisorIssue.objects.create(
        supervisor=supervisor,
        error="Stripe checkout already fulfilled",
        code="stripe-checkout-fulfillment-error",
        params={"bag_id": model.bag.id, "stripe_event_id": stripe_event.id},
    )

    result = stripe_checkout_fulfillment_error(issue.id)

    assert result is True


def test_stripe_checkout_fulfillment_error__returns_retry_when_still_error(database, bc: Breathecode, enable_signals):
    enable_signals()

    model = database.create(user=1, academy=1, bag={"status": "CHECKING"})
    stripe_event = StripeEvent.objects.create(
        stripe_id="evt_still_error",
        type="checkout.session.completed",
        status="ERROR",
        status_texts={"payments.stripe_checkout_payment_fulfillment": "missing metadata"},
        data=_checkout_event_data(bag_id=model.bag.id, session_id="cs_still_error")["data"],
        created_at=UTC_NOW - timedelta(minutes=10),
    )

    supervise_stripe_checkout_events_in_error()
    issue = SupervisorIssue.objects.get()

    result = stripe_checkout_fulfillment_error(issue.id)

    assert result is None
    issue.refresh_from_db()
    assert issue.fixed is None
    stripe_event.refresh_from_db()
    assert stripe_event.status == "ERROR"


def test_stripe_checkout_fulfillment_error__returns_false_when_event_missing(database, bc: Breathecode):
    supervise_stripe_checkout_events_in_error()
    supervisor = SupervisorModel.objects.get(task_name="supervise_stripe_checkout_events_in_error")
    issue = SupervisorIssue.objects.create(
        supervisor=supervisor,
        error="Missing stripe event",
        code="stripe-checkout-fulfillment-error",
        params={"bag_id": 1, "stripe_event_id": 99999},
    )

    result = stripe_checkout_fulfillment_error(issue.id)

    assert result is False


def test_stripe_checkout_fulfillment_error__returns_false_when_bag_paid_by_other_session(database, bc: Breathecode):
    model = database.create(user=1, academy=1, bag={"status": "PAID", "was_delivered": True})
    Invoice.objects.create(
        user=model.user,
        academy=model.academy,
        bag=model.bag,
        currency=model.currency,
        amount=100.0,
        status=Invoice.Status.FULFILLED,
        stripe_id="cs_other_paid",
        paid_at=UTC_NOW - timedelta(minutes=15),
    )
    stripe_event = StripeEvent.objects.create(
        stripe_id="evt_stale_paid_bag",
        type="checkout.session.completed",
        status="ERROR",
        status_texts={"payments.stripe_checkout_payment_fulfillment": "transient error"},
        data=_checkout_event_data(bag_id=model.bag.id, session_id="cs_stale_paid_bag")["data"],
        created_at=UTC_NOW - timedelta(minutes=10),
    )

    supervise_stripe_checkout_events_in_error()
    issue = SupervisorIssue.objects.get()

    result = stripe_checkout_fulfillment_error(issue.id)

    assert result is False
