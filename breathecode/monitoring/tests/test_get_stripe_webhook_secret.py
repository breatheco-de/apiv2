import json

import pytest

from breathecode.monitoring.views import get_stripe_webhook_secret
from breathecode.payments.models import AcademyPaymentSettings


pytestmark = pytest.mark.django_db(reset_sequences=True)


def _checkout_payload(*, object_id="cs_test_123", metadata=None):
    return {
        "id": "evt_test",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": object_id,
                "metadata": metadata or {},
            }
        },
    }


def _set_academy_secret(academy, secret):
    AcademyPaymentSettings.objects.update_or_create(
        academy=academy,
        defaults={"stripe_webhook_secret": secret},
    )


def test_falls_back_to_global_secret_when_payload_is_empty(monkeypatch):
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_global")

    assert get_stripe_webhook_secret() == "whsec_global"


def test_uses_academy_secret_from_checkout_bag_metadata(database, monkeypatch):
    monkeypatch.delenv("STRIPE_WEBHOOK_SECRET", raising=False)

    model = database.create(user=1, academy=1, currency=1, bag=1)
    _set_academy_secret(model.academy, "whsec_from_bag")

    payload = _checkout_payload(metadata={"bag_id": str(model.bag.id), "amount": "100.0"})

    assert get_stripe_webhook_secret(json.dumps(payload).encode("utf-8")) == "whsec_from_bag"


def test_uses_academy_secret_from_invoice_stripe_id(database, monkeypatch):
    monkeypatch.delenv("STRIPE_WEBHOOK_SECRET", raising=False)

    model = database.create(user=1, academy=1, currency=1, bag=1, invoice=1)
    _set_academy_secret(model.academy, "whsec_from_invoice")

    model.invoice.stripe_id = "cs_existing_session"
    model.invoice.save()

    payload = _checkout_payload(object_id="cs_existing_session")

    assert get_stripe_webhook_secret(payload) == "whsec_from_invoice"
