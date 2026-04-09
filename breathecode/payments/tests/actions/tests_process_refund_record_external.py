from types import SimpleNamespace

from breathecode.payments import actions


class DummyInvoice:
    def __init__(self):
        self.id = 42
        self.amount = 100.0
        self.amount_refunded = 0.0
        self.status = actions.Invoice.Status.FULFILLED
        self.refunded_at = None
        self.stripe_id = "ch_test_123"
        self.currency = SimpleNamespace(code="USD")
        self.bag = SimpleNamespace(country_code="US")
        self.user = SimpleNamespace(id=1, email="student@example.com")
        self.amount_breakdown = {"plans": {}, "service-items": {}}

    def save(self):
        return None


def test_process_refund_record_external_does_not_call_stripe_and_updates_invoice(monkeypatch):
    created = {}
    stripe_calls = {"count": 0}

    class DummyCreditNote:
        class Status:
            ISSUED = "ISSUED"

        class _Manager:
            @staticmethod
            def create(**kwargs):
                created.update(kwargs)
                return SimpleNamespace(**kwargs)

        objects = _Manager()

    def _unexpected_stripe_call(*args, **kwargs):
        stripe_calls["count"] += 1
        raise AssertionError("Stripe refund should not be called in record external flow")

    monkeypatch.setattr(actions, "CreditNote", DummyCreditNote)
    monkeypatch.setattr("breathecode.payments.services.stripe.Stripe.refund_payment", _unexpected_stripe_call, raising=False)

    invoice = DummyInvoice()
    credit_note = actions.process_refund_record_external(
        invoice=invoice,
        amount=25.0,
        items_to_refund={},
        external_reference="ticket-123",
        stripe_refund_id="re_external_123",
        reason="Refund completed outside the API",
        lang="en",
    )

    assert stripe_calls["count"] == 0
    assert invoice.amount_refunded == 25.0
    assert invoice.status == actions.Invoice.Status.PARTIALLY_REFUNDED
    assert created["refund_stripe_id"] == "re_external_123"
    assert created["breakdown"]["external-refund"]["recorded_externally"] is True
    assert created["breakdown"]["external-refund"]["external_reference"] == "ticket-123"
    assert credit_note.refund_stripe_id == "re_external_123"

