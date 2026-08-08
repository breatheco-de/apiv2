from datetime import date, timedelta
from decimal import Decimal

import pytest
from capyc.rest_framework.exceptions import ValidationException
from django.utils import timezone

from breathecode.payments.actions import generate_active_users_bill, get_active_users_month_invoice
from breathecode.payments.models import ActiveUsersBill, AcademyPaymentSettings


def _enable_billing(academy, price=10, patterns=None):
    return AcademyPaymentSettings.objects.create(
        academy=academy,
        internal_billing={
            "active_users_billing": {
                "enabled": True,
                "price_per_user": price,
                "currency": "USD",
                "exclude_cohort_slug_patterns": patterns or [],
            }
        },
    )


@pytest.mark.django_db
def test_generate_requires_settings(database):
    model = database.create(academy=1, city=1, country=1)
    with pytest.raises(ValidationException, match="academy-payment-settings-not-found"):
        generate_active_users_bill(model.academy)


@pytest.mark.django_db
def test_generate_requires_enabled(database):
    model = database.create(academy=1, city=1, country=1)
    AcademyPaymentSettings.objects.create(
        academy=model.academy,
        internal_billing={"active_users_billing": {"enabled": False, "price_per_user": 10}},
    )
    with pytest.raises(ValidationException, match="active-users-billing-disabled"):
        generate_active_users_bill(model.academy)


@pytest.mark.django_db
def test_generate_counts_active_and_not_completing_excludes_late(database):
    model = database.create(
        user=3,
        academy=1,
        city=1,
        country=1,
        cohort={"stage": "STARTED"},
        cohort_user=[
            {"user_id": 1, "role": "STUDENT", "educational_status": "ACTIVE", "finantial_status": "UP_TO_DATE"},
            {"user_id": 2, "role": "STUDENT", "educational_status": "NOT_COMPLETING", "finantial_status": None},
            {"user_id": 3, "role": "STUDENT", "educational_status": "ACTIVE", "finantial_status": "LATE"},
        ],
    )
    _enable_billing(model.academy, price=10)
    billing_date = date(2026, 8, 7)
    bill = generate_active_users_bill(model.academy, billing_date=billing_date)

    assert bill.unique_user_count == 2
    assert bill.total_amount == Decimal("20.00")
    assert bill.price_per_user == Decimal("10")
    assert bill.items.count() == 1
    assert bill.items.first().user_count == 2


@pytest.mark.django_db
def test_generate_excludes_ended_cohorts(database):
    model = database.create(
        user=2,
        academy=1,
        city=1,
        country=1,
        cohort=[
            {"slug": "active-cohort", "stage": "STARTED"},
            {"slug": "ended-cohort", "stage": "ENDED"},
        ],
        cohort_user=[
            {
                "user_id": 1,
                "cohort_id": 1,
                "role": "STUDENT",
                "educational_status": "ACTIVE",
                "finantial_status": "UP_TO_DATE",
            },
            {
                "user_id": 2,
                "cohort_id": 2,
                "role": "STUDENT",
                "educational_status": "ACTIVE",
                "finantial_status": "UP_TO_DATE",
            },
        ],
    )
    _enable_billing(model.academy, price=10)
    bill = generate_active_users_bill(model.academy, billing_date=date(2026, 8, 7))

    assert bill.unique_user_count == 1
    assert bill.items.count() == 1
    assert bill.items.first().cohort.slug == "active-cohort"


@pytest.mark.django_db
def test_generate_excludes_cohort_slug_patterns(database):
    model = database.create(
        user=2,
        academy=1,
        city=1,
        country=1,
        cohort=[
            {"slug": "web-dev-pt-01", "stage": "STARTED"},
            {"slug": "land-a-job-in-tech-miami", "stage": "STARTED"},
        ],
        cohort_user=[
            {
                "user_id": 1,
                "cohort_id": 1,
                "role": "STUDENT",
                "educational_status": "ACTIVE",
                "finantial_status": "FULLY_PAID",
            },
            {
                "user_id": 2,
                "cohort_id": 2,
                "role": "STUDENT",
                "educational_status": "ACTIVE",
                "finantial_status": "UP_TO_DATE",
            },
        ],
    )
    _enable_billing(model.academy, price=5, patterns=[".*land-a-job-in-tech.*"])
    bill = generate_active_users_bill(model.academy, billing_date=date(2026, 8, 7))

    assert bill.unique_user_count == 1
    assert "land-a-job-in-tech" in bill.notes
    assert bill.items.count() == 1
    assert bill.items.first().cohort.slug == "web-dev-pt-01"


@pytest.mark.django_db
def test_generate_dedupes_across_cohorts(database):
    model = database.create(
        user=1,
        academy=1,
        city=1,
        country=1,
        cohort=[
            {"slug": "cohort-a", "stage": "STARTED"},
            {"slug": "cohort-b", "stage": "STARTED"},
        ],
        cohort_user=[
            {
                "user_id": 1,
                "cohort_id": 1,
                "role": "STUDENT",
                "educational_status": "ACTIVE",
                "finantial_status": "UP_TO_DATE",
            },
            {
                "user_id": 1,
                "cohort_id": 2,
                "role": "STUDENT",
                "educational_status": "ACTIVE",
                "finantial_status": "UP_TO_DATE",
            },
        ],
    )
    _enable_billing(model.academy, price=10)
    bill = generate_active_users_bill(model.academy, billing_date=date(2026, 8, 7))

    assert bill.unique_user_count == 1
    assert bill.duplicate_user_count == 1
    assert "duplicate" in bill.notes.lower()
    # First cohort wins; second cohort has no attributed users so no item (or only notes)
    items = list(bill.items.all())
    assert len(items) == 1
    assert items[0].cohort.slug == "cohort-a"
    assert items[0].user_count == 1


@pytest.mark.django_db
def test_generate_idempotent(database):
    model = database.create(
        user=1,
        academy=1,
        city=1,
        country=1,
        cohort={"stage": "STARTED"},
        cohort_user={
            "role": "STUDENT",
            "educational_status": "ACTIVE",
            "finantial_status": "UP_TO_DATE",
        },
    )
    _enable_billing(model.academy)
    d = date(2026, 8, 7)
    bill1 = generate_active_users_bill(model.academy, billing_date=d)
    bill2 = generate_active_users_bill(model.academy, billing_date=d)
    assert bill1.id == bill2.id
    assert ActiveUsersBill.objects.filter(academy=model.academy, billing_date=d).count() == 1


@pytest.mark.django_db
def test_month_invoice_peak_day_and_items(database):
    model = database.create(academy=1, city=1, country=1, cohort={"stage": "STARTED"})
    _enable_billing(model.academy, price=10)

    low = ActiveUsersBill.objects.create(
        academy=model.academy,
        billing_date=date(2026, 8, 1),
        unique_user_count=10,
        price_per_user=Decimal("10.00"),
        total_amount=Decimal("100.00"),
        currency_code="USD",
        title="low",
    )
    peak = ActiveUsersBill.objects.create(
        academy=model.academy,
        billing_date=date(2026, 8, 14),
        unique_user_count=42,
        price_per_user=Decimal("10.00"),
        total_amount=Decimal("420.00"),
        currency_code="USD",
        title="peak",
        notes="7 duplicates disregarded",
    )
    ActiveUsersBill.objects.create(
        academy=model.academy,
        billing_date=date(2026, 8, 20),
        unique_user_count=42,
        price_per_user=Decimal("10.00"),
        total_amount=Decimal("420.00"),
        currency_code="USD",
        title="tie-later",
    )
    ignored = ActiveUsersBill.objects.create(
        academy=model.academy,
        billing_date=date(2026, 8, 15),
        unique_user_count=100,
        price_per_user=Decimal("10.00"),
        total_amount=Decimal("1000.00"),
        currency_code="USD",
        status="IGNORED",
        title="ignored",
    )

    from breathecode.payments.models import ActiveUsersBillItem

    item = ActiveUsersBillItem.objects.create(
        bill=peak,
        cohort=model.cohort,
        user_count=42,
        amount=Decimal("420.00"),
        user_ids=[1, 2],
        notes="peak item",
    )

    payload = get_active_users_month_invoice(model.academy, 2026, 8)
    assert payload["peak_date"] == "2026-08-14"
    assert payload["peak_bill_id"] == peak.id
    assert payload["unique_user_count"] == 42
    assert payload["amount"] == "420.00"
    assert len(payload["items"]) == 1
    assert payload["items"][0]["id"] == item.id
    assert payload["items"][0]["cohort"]["slug"] == model.cohort.slug
    assert payload["items"][0]["user_count"] == 42
    assert any(d["id"] == low.id for d in payload["days"])
    assert not any(d["id"] == ignored.id for d in payload["days"])
    assert "2026-08-14" in payload["notes"]
