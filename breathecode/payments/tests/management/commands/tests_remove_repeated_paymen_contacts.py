import pytest
from django.core.management import call_command
import capyc.pytest as capyc
from io import StringIO
from breathecode.payments.models import PaymentContact


@pytest.mark.django_db
def test_remove_repeated_payment_contacts_removes_duplicates(database):
    model = database.create(
        city=1,
        country=1,
        academy={
            "id": 47,
            "name": "Test Academy",
            "slug": "test-academy",
            "logo_url": "https://example.com/logo.png",
            "street_address": "123 Test St",
            "city": 1,
            "country": 1,
        },
        user=1,
    )

    # Create first payment contact
    contact1 = PaymentContact.objects.create(user=model.user, stripe_id="cus_1234567890abcdef", academy=model.academy)

    # Create second payment contact
    contact2 = PaymentContact.objects.create(user=model.user, stripe_id="cus_abcdef1234567890", academy=None)

    out = StringIO()
    call_command("remove_repeated_payment_contacts", stdout=out)

    # Only the oldest one should remain
    contacts = PaymentContact.objects.filter(user=model.user)
    assert contacts.count() == 1
    assert contacts.first().academy_id == 47
    assert "Deleted repeated contacts" in out.getvalue()
    assert f"{model.user.email} (ID: {contact2.id})" in out.getvalue()


def test_remove_repeated_payment_contacts_no_duplicates(database: capyc.Database):
    model = database.create(
        city=1,
        country=1,
        academy={
            "id": 47,
            "name": "Test Academy",
            "slug": "test-academy",
            "logo_url": "https://example.com/logo.png",
            "street_address": "123 Test St",
            "city": 1,
            "country": 1,
        },
        user=1,
    )

    model2 = database.create(
        payment_contact={
            "user": 1,
            "stripe_id": "cus_1234567890abcdef",
            "academy": model.academy,
        }
    )

    out = StringIO()
    call_command("remove_repeated_payment_contacts", stdout=out)

    assert "No repeated contacts found to delete." in out.getvalue()


def test_remove_repeated_payment_contacts_academy_not_exists(database: capyc.Database):
    model = database.create(user=1, payment_contact=1)

    out = StringIO()
    call_command("remove_repeated_payment_contacts", stdout=out)

    assert "Academy with id 47 does not exist." in out.getvalue()
