from datetime import datetime
from unittest.mock import MagicMock, call

import pytest

from breathecode.notify import tasks
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode


@pytest.fixture(autouse=True)
def mocks(db, monkeypatch):
    m1 = MagicMock()
    monkeypatch.setattr(tasks.async_deliver_hook, "delay", m1)
    yield m1


@pytest.fixture(autouse=True)
def base(db, bc: Breathecode):
    model = bc.database.create(
        hook={"event": "subscription.subscription_created"},
        user={"username": "test"},
        academy={
            "slug": "test",
            "available_as_saas": True,
        },
    )
    yield model


def serializer(subscription, user=None, academy=None):
    academy_obj = None
    if academy:
        academy_obj = {
            "id": academy.id,
            "name": academy.name,
            "slug": academy.slug,
        }

    user_obj = None
    if user:
        user_obj = {
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
        }

    return {
        "id": subscription.id,
        "status": subscription.status,
        "status_message": subscription.status_message,
        "user": user_obj,
        "academy": academy_obj,
        "selected_cohort_set": subscription.selected_cohort_set,
        "selected_mentorship_service_set": subscription.selected_mentorship_service_set,
        "selected_event_type_set": subscription.selected_event_type_set,
        "plans": [],
        "invoices": [],
        "next_payment_at": subscription.next_payment_at,
        "valid_until": subscription.valid_until,
        "paid_at": subscription.paid_at,
        "is_refundable": subscription.is_refundable,
        "pay_every": subscription.pay_every,
        "pay_every_unit": subscription.pay_every_unit,
    }


def test_nothing_happens(bc: Breathecode, enable_signals, enable_hook_manager, mocks, base):
    enable_signals("breathecode.payments.signals.subscription_created")
    enable_hook_manager()

    mock = mocks
    model = bc.database.create(
        subscription=2,
        user=base.user,
        academy=base.academy,
    )

    assert bc.database.list_of("payments.subscription") == bc.format.to_dict(model.subscription)

    assert mock.call_args_list == [
        call(base.hook.target, serializer(model.subscription[0], user=model.user, academy=model.academy), hook_id=1),
        call(base.hook.target, serializer(model.subscription[1], user=model.user, academy=model.academy), hook_id=1),
    ]
