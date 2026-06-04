from breathecode.payments.serializers import GetInvoiceSerializer, GetInvoiceSmallSerializer


def test_invoice_serializers_include_invoice_notes(database):
    model = database.create(
        user=1,
        academy=1,
        city=1,
        country=1,
        currency=1,
        bag=1,
        invoice={"invoice_notes": "Note made by user 1: Staff discount approved"},
    )

    assert GetInvoiceSmallSerializer(model.invoice, many=False).data["invoice_notes"] == (
        "Note made by user 1: Staff discount approved"
    )
    assert GetInvoiceSerializer(model.invoice, many=False).data["invoice_notes"] == (
        "Note made by user 1: Staff discount approved"
    )


def test_get_invoice_serializer_includes_stripe_id(database):
    model = database.create(
        user=1,
        academy=1,
        city=1,
        country=1,
        currency=1,
        bag=1,
        invoice={"stripe_id": "ch_test_abc123"},
    )

    data = GetInvoiceSerializer(model.invoice, many=False).data
    assert data["stripe_id"] == "ch_test_abc123"
    assert "stripe_id" not in GetInvoiceSmallSerializer(model.invoice, many=False).data
