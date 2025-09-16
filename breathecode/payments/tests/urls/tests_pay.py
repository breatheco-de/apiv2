import math
import random
import re
from datetime import UTC, timedelta
from unittest.mock import MagicMock, call, patch

import pytest
import stripe
from dateutil.relativedelta import relativedelta
from django.urls import reverse_lazy
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

import breathecode.activity.tasks as activity_tasks
from breathecode.admissions import tasks as admissions_tasks
from breathecode.payments import tasks
from breathecode.payments.actions import apply_pricing_ratio, calculate_relative_delta
from breathecode.payments.models import ServiceItem
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode

UTC_NOW = timezone.now()


def format_user_setting(data={}):
    return {
        "id": 1,
        "user_id": 1,
        "main_currency_id": None,
        "lang": "en",
        **data,
    }


def format_invoice_item(data={}):
    return {
        "academy_id": 1,
        "amount": 0.0,
        "currency_id": 1,
        "bag_id": 1,
        "id": 1,
        "paid_at": UTC_NOW,
        "status": "FULFILLED",
        "stripe_id": None,
        "user_id": 1,
        "refund_stripe_id": None,
        "refunded_at": None,
        "externally_managed": False,
        "payment_method_id": None,
        "proof_id": None,
        **data,
    }


def to_iso(date):
    return re.sub(r"\+00:00$", "Z", date.replace(tzinfo=UTC).isoformat())


def format_coupon(coupon, data={}):
    return {
        "auto": coupon.auto,
        "discount_type": coupon.discount_type,
        "discount_value": coupon.discount_value,
        "expires_at": to_iso(coupon.expires_at) if coupon.expires_at else None,
        "offered_at": to_iso(coupon.offered_at) if coupon.offered_at else None,
        "referral_type": coupon.referral_type,
        "referral_value": coupon.referral_value,
        "slug": coupon.slug,
        **data,
    }


def get_serializer(bc, currency, user, coupons=[], data={}):
    return {
        "id": 1,
        "amount": 0,
        "currency": {
            "code": currency.code,
            "name": currency.name,
        },
        "paid_at": bc.datetime.to_iso_string(UTC_NOW),
        "status": "FULFILLED",
        "user": {
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
        },
        "coupons": [format_coupon(x) for x in coupons],
        **data,
    }


def generate_amounts_by_time(over_50=False):
    if over_50:
        return {
            "amount_per_month": random.random() * 50 + 50,
            "amount_per_quarter": random.random() * 50 + 50,
            "amount_per_half": random.random() * 50 + 50,
            "amount_per_year": random.random() * 50 + 50,
        }

    return {
        "amount_per_month": random.random() * 100 + 1,
        "amount_per_quarter": random.random() * 100 + 1,
        "amount_per_half": random.random() * 100 + 1,
        "amount_per_year": random.random() * 100 + 1,
    }


def which_amount_is_zero(data={}):
    for key in data:
        if key == "amount_per_quarter":
            return "MONTH", 1


CHOSEN_PERIOD = {
    "MONTH": "amount_per_month",
    "QUARTER": "amount_per_quarter",
    "HALF": "amount_per_half",
    "YEAR": "amount_per_year",
}


def get_amount_per_period(period, data):
    return data[CHOSEN_PERIOD[period]]


def invoice_mock():

    class FakeInvoice:
        id = 1
        amount = 100

    return FakeInvoice()


@pytest.fixture(autouse=True)
def get_patch(db, monkeypatch):
    monkeypatch.setattr(activity_tasks.add_activity, "delay", MagicMock())
    monkeypatch.setattr("breathecode.admissions.tasks.build_cohort_user.delay", MagicMock())
    monkeypatch.setattr("breathecode.admissions.tasks.build_profile_academy.delay", MagicMock())
    monkeypatch.setattr("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    monkeypatch.setattr("breathecode.payments.tasks.build_subscription.delay", MagicMock())
    monkeypatch.setattr("breathecode.payments.tasks.build_plan_financing.delay", MagicMock())
    monkeypatch.setattr("breathecode.payments.tasks.build_free_subscription.delay", MagicMock())
    monkeypatch.setattr("stripe.Charge.create", MagicMock(return_value={"id": 1}))
    monkeypatch.setattr("stripe.Customer.create", MagicMock(return_value={"id": 1}))

    def wrapper(charge={}, customer={}):
        monkeypatch.setattr("stripe.Charge.create", MagicMock(return_value=charge))
        monkeypatch.setattr("stripe.Customer.create", MagicMock(return_value=customer))

    yield wrapper


def test_without_auth(bc: Breathecode, client: APIClient):
    url = reverse_lazy("payments:pay")
    response = client.post(url)

    json = response.json()
    expected = {
        "detail": "Authentication credentials were not provided.",
        "status_code": 401,
    }

    assert json == expected
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    assert bc.database.list_of("payments.Bag") == []
    assert bc.database.list_of("authenticate.UserSetting") == []

    bc.check.calls(admissions_tasks.build_cohort_user.delay.call_args_list, [])
    bc.check.calls(admissions_tasks.build_profile_academy.delay.call_args_list, [])
    bc.check.calls(activity_tasks.add_activity.delay.call_args_list, [])


@pytest.mark.parametrize("in_4geeks", [True, False])
@pytest.mark.parametrize("bad_reputation", ["BAD", "FRAUD"])
@pytest.mark.parametrize("good_reputation", ["GOOD", "UNKNOWN"])
def test_fraud_case(bc: Breathecode, client: APIClient, in_4geeks, bad_reputation, good_reputation):
    if in_4geeks:
        financial_reputation = {
            "in_4geeks": bad_reputation,
            "in_stripe": good_reputation,
        }
    else:
        financial_reputation = {
            "in_4geeks": good_reputation,
            "in_stripe": bad_reputation,
        }

    model = bc.database.create(user=1, financial_reputation=financial_reputation)
    client.force_authenticate(user=model.user)

    url = reverse_lazy("payments:pay")
    response = client.post(url)

    json = response.json()
    expected = {
        "detail": "fraud-or-bad-reputation",
        "status_code": 402,
        "silent": True,
        "silent_code": "fraud-or-bad-reputation",
    }

    assert json == expected
    assert response.status_code == status.HTTP_402_PAYMENT_REQUIRED

    assert bc.database.list_of("payments.Bag") == []
    assert bc.database.list_of("payments.Invoice") == []
    assert bc.database.list_of("authenticate.UserSetting") == [
        format_user_setting({"lang": "en"}),
    ]

    bc.check.calls(admissions_tasks.build_cohort_user.delay.call_args_list, [])
    bc.check.calls(admissions_tasks.build_profile_academy.delay.call_args_list, [])
    bc.check.calls(activity_tasks.add_activity.delay.call_args_list, [])


@pytest.mark.parametrize("reputation1", ["GOOD", "UNKNOWN"])
@pytest.mark.parametrize("reputation2", ["GOOD", "UNKNOWN"])
def test_no_token(bc: Breathecode, client: APIClient, reputation1, reputation2):
    financial_reputation = {
        "in_4geeks": reputation1,
        "in_stripe": reputation2,
    }

    model = bc.database.create(user=1, financial_reputation=financial_reputation)
    client.force_authenticate(user=model.user)

    url = reverse_lazy("payments:pay")
    response = client.post(url)

    json = response.json()
    expected = {"detail": "missing-token", "status_code": 404}

    assert json == expected
    assert response.status_code == status.HTTP_404_NOT_FOUND

    assert bc.database.list_of("payments.Bag") == []
    assert bc.database.list_of("payments.Invoice") == []
    assert bc.database.list_of("authenticate.UserSetting") == [
        format_user_setting({"lang": "en"}),
    ]

    bc.check.calls(admissions_tasks.build_cohort_user.delay.call_args_list, [])
    bc.check.calls(admissions_tasks.build_profile_academy.delay.call_args_list, [])
    bc.check.calls(activity_tasks.add_activity.delay.call_args_list, [])


def test_without_bag__passing_token(bc: Breathecode, client: APIClient):
    model = bc.database.create(user=1)
    client.force_authenticate(user=model.user)

    url = reverse_lazy("payments:pay")
    data = {"token": "xdxdxdxdxdxdxdxdxdxd"}
    response = client.post(url, data, format="json")

    json = response.json()
    expected = {"detail": "not-found-or-without-checking", "status_code": 404}

    assert json == expected
    assert response.status_code == status.HTTP_404_NOT_FOUND

    assert bc.database.list_of("payments.Bag") == []
    assert bc.database.list_of("payments.Invoice") == []
    assert bc.database.list_of("authenticate.UserSetting") == [
        format_user_setting({"lang": "en"}),
    ]

    bc.check.calls(admissions_tasks.build_cohort_user.delay.call_args_list, [])
    bc.check.calls(admissions_tasks.build_profile_academy.delay.call_args_list, [])
    bc.check.calls(activity_tasks.add_activity.delay.call_args_list, [])


def test_no_bag(bc: Breathecode, client: APIClient):
    bag = {
        "token": "xdxdxdxdxdxdxdxdxdxd",
        "expires_at": UTC_NOW,
        "status": "CHECKING",
        "type": "BAG",
        "seat_service_item_id": None,
    }
    model = bc.database.create(user=1, bag=bag, currency=1, academy=1)
    client.force_authenticate(user=model.user)

    url = reverse_lazy("payments:pay")
    data = {"token": "xdxdxdxdxdxdxdxdxdxd"}
    response = client.post(url, data, format="json")

    json = response.json()
    expected = {"detail": "bag-is-empty", "status_code": 400}

    assert json == expected
    assert response.status_code == status.HTTP_400_BAD_REQUEST

    assert bc.database.list_of("payments.Bag") == [bc.format.to_dict(model.bag)]
    assert bc.database.list_of("payments.Invoice") == []
    assert bc.database.list_of("authenticate.UserSetting") == [
        format_user_setting({"lang": "en"}),
    ]

    bc.check.queryset_with_pks(model.bag.plans.all(), [])
    bc.check.queryset_with_pks(model.bag.service_items.all(), [])

    bc.check.calls(admissions_tasks.build_cohort_user.delay.call_args_list, [])
    bc.check.calls(admissions_tasks.build_profile_academy.delay.call_args_list, [])
    bc.check.calls(
        activity_tasks.add_activity.delay.call_args_list,
        [
            call(1, "bag_created", related_type="payments.Bag", related_id=1),
        ],
    )


def test_with_bag__no_free_trial(bc: Breathecode, client: APIClient):
    bag = {
        "token": "xdxdxdxdxdxdxdxdxdxd",
        "expires_at": UTC_NOW,
        "status": "CHECKING",
        "type": "BAG",
        random.choice(
            [
                "amount_per_month",
                "amount_per_quarter",
                "amount_per_half",
                "amount_per_year",
            ]
        ): 1,
        "seat_service_item_id": None,
    }

    plan = {"is_renewable": False}

    model = bc.database.create(user=1, bag=bag, academy=1, currency=1, plan=plan, service_item=1)
    client.force_authenticate(user=model.user)

    url = reverse_lazy("payments:pay")
    data = {"token": "xdxdxdxdxdxdxdxdxdxd"}
    response = client.post(url, data, format="json")

    json = response.json()
    expected = {"detail": "missing-chosen-period", "status_code": 400}

    assert json == expected
    assert response.status_code == status.HTTP_400_BAD_REQUEST

    assert bc.database.list_of("payments.Bag") == [bc.format.to_dict(model.bag)]
    assert bc.database.list_of("payments.Invoice") == []
    assert bc.database.list_of("authenticate.UserSetting") == [
        format_user_setting({"lang": "en"}),
    ]

    bc.check.queryset_with_pks(model.bag.plans.all(), [1])
    bc.check.queryset_with_pks(model.bag.service_items.all(), [1])

    bc.check.calls(admissions_tasks.build_cohort_user.delay.call_args_list, [])
    bc.check.calls(admissions_tasks.build_profile_academy.delay.call_args_list, [])
    bc.check.calls(
        activity_tasks.add_activity.delay.call_args_list,
        [
            call(1, "bag_created", related_type="payments.Bag", related_id=1),
        ],
    )


def test_bad_choosen_period(bc: Breathecode, client: APIClient):
    bag = {
        "token": "xdxdxdxdxdxdxdxdxdxd",
        "expires_at": UTC_NOW,
        "status": "CHECKING",
        "type": "BAG",
        "seat_service_item_id": None,
    }

    plan = {"is_renewable": False}

    model = bc.database.create(user=1, bag=bag, academy=1, currency=1, plan=plan, service_item=1)
    client.force_authenticate(user=model.user)

    url = reverse_lazy("payments:pay")
    data = {"token": "xdxdxdxdxdxdxdxdxdxd", "chosen_period": bc.fake.slug()}
    response = client.post(url, data, format="json")

    json = response.json()
    expected = {"detail": "invalid-chosen-period", "status_code": 400}

    assert json == expected
    assert response.status_code == status.HTTP_400_BAD_REQUEST

    assert bc.database.list_of("payments.Bag") == [bc.format.to_dict(model.bag)]
    assert bc.database.list_of("payments.Invoice") == []
    assert bc.database.list_of("authenticate.UserSetting") == [
        format_user_setting({"lang": "en"}),
    ]

    bc.check.queryset_with_pks(model.bag.plans.all(), [1])
    bc.check.queryset_with_pks(model.bag.service_items.all(), [1])

    bc.check.calls(admissions_tasks.build_cohort_user.delay.call_args_list, [])
    bc.check.calls(admissions_tasks.build_profile_academy.delay.call_args_list, [])
    bc.check.calls(
        activity_tasks.add_activity.delay.call_args_list,
        [
            call(1, "bag_created", related_type="payments.Bag", related_id=1),
        ],
    )


def test_free_trial__no_plan_offer(bc: Breathecode, client: APIClient):
    bag = {
        "token": "xdxdxdxdxdxdxdxdxdxd",
        "expires_at": UTC_NOW,
        "status": "CHECKING",
        "type": "BAG",
        "seat_service_item_id": None,
    }

    plan = {"is_renewable": False}

    model = bc.database.create(user=1, bag=bag, academy=1, currency=1, plan=plan, service_item=1)
    client.force_authenticate(user=model.user)

    url = reverse_lazy("payments:pay")
    data = {
        "token": "xdxdxdxdxdxdxdxdxdxd",
    }
    response = client.post(url, data, format="json")

    json = response.json()
    expected = {
        "detail": "the-plan-was-chosen-is-not-ready-too-be-sold",
        "status_code": 400,
    }

    assert json == expected
    assert response.status_code == status.HTTP_400_BAD_REQUEST

    assert bc.database.list_of("payments.Bag") == [
        bc.format.to_dict(model.bag),
    ]
    assert bc.database.list_of("payments.Invoice") == []
    assert bc.database.list_of("authenticate.UserSetting") == [
        format_user_setting({"lang": "en"}),
    ]

    bc.check.queryset_with_pks(model.bag.plans.all(), [1])
    bc.check.queryset_with_pks(model.bag.service_items.all(), [1])
    assert tasks.build_subscription.delay.call_args_list == []
    assert tasks.build_plan_financing.delay.call_args_list == []
    assert tasks.build_free_subscription.delay.call_args_list == []

    bc.check.calls(admissions_tasks.build_cohort_user.delay.call_args_list, [])
    bc.check.calls(admissions_tasks.build_profile_academy.delay.call_args_list, [])
    bc.check.calls(
        activity_tasks.add_activity.delay.call_args_list,
        [
            call(1, "bag_created", related_type="payments.Bag", related_id=1),
        ],
    )


def test_free_trial__with_plan_offer(bc: Breathecode, client: APIClient):
    bag = {
        "token": "xdxdxdxdxdxdxdxdxdxd",
        "expires_at": UTC_NOW,
        "status": "CHECKING",
        "type": "BAG",
        "seat_service_item_id": None,
    }

    plan = {"is_renewable": False}

    model = bc.database.create(user=1, bag=bag, academy=1, currency=1, plan=plan, service_item=1, plan_offer=1)
    client.force_authenticate(user=model.user)

    url = reverse_lazy("payments:pay")
    data = {
        "token": "xdxdxdxdxdxdxdxdxdxd",
    }
    response = client.post(url, data, format="json")

    json = response.json()
    expected = get_serializer(bc, model.currency, model.user, data={})

    assert json == expected
    assert response.status_code == status.HTTP_201_CREATED

    assert bc.database.list_of("payments.Bag") == [
        {
            **bc.format.to_dict(model.bag),
            "token": None,
            "status": "PAID",
            "expires_at": None,
        }
    ]
    assert bc.database.list_of("payments.Invoice") == [format_invoice_item()]
    assert bc.database.list_of("authenticate.UserSetting") == [
        format_user_setting({"lang": "en"}),
    ]

    bc.check.queryset_with_pks(model.bag.plans.all(), [1])
    bc.check.queryset_with_pks(model.bag.service_items.all(), [1])
    assert tasks.build_subscription.delay.call_args_list == []
    assert tasks.build_plan_financing.delay.call_args_list == []
    assert tasks.build_free_subscription.delay.call_args_list == [call(1, 1, conversion_info="")]

    bc.check.calls(admissions_tasks.build_cohort_user.delay.call_args_list, [])
    bc.check.calls(admissions_tasks.build_profile_academy.delay.call_args_list, [call(1, 1)])
    bc.check.calls(
        activity_tasks.add_activity.delay.call_args_list,
        [
            call(1, "bag_created", related_type="payments.Bag", related_id=1),
            call(1, "checkout_completed", related_type="payments.Invoice", related_id=1),
        ],
    )


def test_seats_pricing_not_configured(bc: Breathecode, client: APIClient):
    # Base bag amounts (will be adjusted by seat add-on below)
    bag = {
        "token": "xdxdxdxdxdxdxdxdxdxd",
        "expires_at": UTC_NOW,
        "status": "CHECKING",
        "type": "BAG",
        **generate_amounts_by_time(over_50=True),
        "seat_service_item_id": 1,
    }
    chosen_period = random.choice(["MONTH", "QUARTER", "HALF", "YEAR"])

    plan = {"is_renewable": False}
    # Random coupons
    random_percent = random.random() * 0.3
    discount1 = random.random() * 20
    discount2 = random.random() * 10
    coupons = [
        {
            "discount_type": "PERCENT_OFF",
            "discount_value": random_percent,
            "offered_at": None,
            "expires_at": None,
        },
        {
            "discount_type": "FIXED_PRICE",
            "discount_value": discount1,
            "offered_at": None,
            "expires_at": None,
        },
        {
            "discount_type": "HAGGLING",
            "discount_value": discount2,
            "offered_at": None,
            "expires_at": None,
        },
    ]
    random.shuffle(coupons)

    # Create base entities
    model = bc.database.create(
        user=1, bag=bag, academy=1, currency=1, plan=plan, service_item=1, coupon=coupons, service={"type": "SEAT"}
    )
    client.force_authenticate(user=model.user)

    # Reuse existing service_item with id=1 as the seat item
    seats = random.randint(1, 5)
    seat_price = random.random() * 20 + 5

    # Compute base amount before adding seat pricing
    base_amount = get_amount_per_period(chosen_period, bc.format.to_dict(model.bag))

    # Simulate that amounts already include per-seat pricing as computed during checking
    seat_total = seat_price * seats
    model.bag.amount_per_month += seat_total
    model.bag.amount_per_quarter += seat_total
    model.bag.amount_per_half += seat_total
    model.bag.amount_per_year += seat_total
    model.bag.save()

    amount = get_amount_per_period(chosen_period, bc.format.to_dict(model.bag))
    assert math.isclose(amount, base_amount + seat_total, rel_tol=1e-9)

    url = reverse_lazy("payments:pay")
    data = {
        "token": "xdxdxdxdxdxdxdxdxdxd",
        "chosen_period": chosen_period,
    }
    response = client.post(url, data, format="json")

    json = response.json()
    expected = {"detail": "price-not-configured-for-per-seat-purchases", "status_code": 400}

    assert json == expected
    assert response.status_code == status.HTTP_400_BAD_REQUEST

    assert bc.database.list_of("payments.Bag") == [
        {
            **bc.format.to_dict(model.bag),
        }
    ]
    assert bc.database.list_of("payments.Invoice") == []
    assert bc.database.list_of("authenticate.UserSetting") == [
        format_user_setting({"lang": "en"}),
    ]

    bc.check.queryset_with_pks(model.bag.plans.all(), [1])
    bc.check.queryset_with_pks(model.bag.service_items.all(), [1])
    # build subscription must be called for chosen_period flow
    assert tasks.build_subscription.delay.call_args_list == []
    assert tasks.build_plan_financing.delay.call_args_list == []
    assert tasks.build_free_subscription.delay.call_args_list == []

    bc.check.calls(admissions_tasks.build_cohort_user.delay.call_args_list, [])
    bc.check.calls(admissions_tasks.build_profile_academy.delay.call_args_list, [])
    bc.check.calls(
        activity_tasks.add_activity.delay.call_args_list,
        [
            call(1, "bag_created", related_type="payments.Bag", related_id=1),
        ],
    )


def test_amount_set_with_subscription_seats(bc: Breathecode, client: APIClient):
    # Base bag amounts (will be adjusted by seat add-on below)
    bag = {
        "token": "xdxdxdxdxdxdxdxdxdxd",
        "expires_at": UTC_NOW,
        "status": "CHECKING",
        "type": "BAG",
        **generate_amounts_by_time(over_50=True),
        "seat_service_item_id": 1,
    }
    chosen_period = random.choice(["MONTH", "QUARTER", "HALF", "YEAR"])

    plan = {"is_renewable": False}
    # Random coupons
    random_percent = random.random() * 0.3
    discount1 = random.random() * 20
    discount2 = random.random() * 10
    coupons = [
        {
            "discount_type": "PERCENT_OFF",
            "discount_value": random_percent,
            "offered_at": None,
            "expires_at": None,
        },
        {
            "discount_type": "FIXED_PRICE",
            "discount_value": discount1,
            "offered_at": None,
            "expires_at": None,
        },
        {
            "discount_type": "HAGGLING",
            "discount_value": discount2,
            "offered_at": None,
            "expires_at": None,
        },
    ]
    random.shuffle(coupons)

    seat_price = random.random() * 20 + 5
    # Reuse existing service_item with id=1 as the seat item
    seats = random.randint(1, 5)

    # Create base entities
    model = bc.database.create(
        user=1,
        bag=bag,
        academy=1,
        currency=1,
        plan=plan,
        service_item={"how_many": seats},
        coupon=coupons,
        service={"type": "SEAT"},
        academy_service={"price_per_unit": seat_price},
    )
    client.force_authenticate(user=model.user)

    # Compute base amount before adding seat pricing
    base_amount = get_amount_per_period(chosen_period, bc.format.to_dict(model.bag))

    # Seats total per month
    seat_total = seat_price * seats
    # Compute expected amount using chosen period factor without mutating bag amounts
    period_factor = (
        1 if chosen_period == "MONTH" else 3 if chosen_period == "QUARTER" else 6 if chosen_period == "HALF" else 12
    )
    amount = base_amount + seat_total * period_factor

    url = reverse_lazy("payments:pay")
    data = {
        "token": "xdxdxdxdxdxdxdxdxdxd",
        "chosen_period": chosen_period,
    }
    response = client.post(url, data, format="json")

    json = response.json()
    total = amount - (amount * random_percent) - discount1 - discount2
    expected = get_serializer(bc, model.currency, model.user, coupons=model.coupon, data={"amount": total})

    assert json == expected
    assert response.status_code == status.HTTP_201_CREATED

    assert bc.database.list_of("payments.Bag") == [
        {
            **bc.format.to_dict(model.bag),
            "token": None,
            "status": "PAID",
            "expires_at": None,
            "chosen_period": chosen_period,
            "is_recurrent": True,
        }
    ]
    assert bc.database.list_of("payments.Invoice") == [
        format_invoice_item(
            {
                "amount": total,
                "stripe_id": "1",
            }
        ),
    ]
    assert bc.database.list_of("authenticate.UserSetting") == [
        format_user_setting({"lang": "en"}),
    ]

    bc.check.queryset_with_pks(model.bag.plans.all(), [1])
    bc.check.queryset_with_pks(model.bag.service_items.all(), [1])
    # build subscription must be called for chosen_period flow
    assert tasks.build_subscription.delay.call_args_list == [call(1, 1, conversion_info="")]
    assert tasks.build_plan_financing.delay.call_args_list == []
    assert tasks.build_free_subscription.delay.call_args_list == []

    bc.check.calls(admissions_tasks.build_cohort_user.delay.call_args_list, [])
    bc.check.calls(admissions_tasks.build_profile_academy.delay.call_args_list, [call(1, 1)])
    bc.check.calls(
        activity_tasks.add_activity.delay.call_args_list,
        [
            call(1, "bag_created", related_type="payments.Bag", related_id=1),
            call(1, "checkout_completed", related_type="payments.Invoice", related_id=1),
        ],
    )


def test_free_trial__with_plan_offer_with_conversion_info(bc: Breathecode, client: APIClient):
    bag = {
        "token": "xdxdxdxdxdxdxdxdxdxd",
        "expires_at": UTC_NOW,
        "status": "CHECKING",
        "type": "BAG",
        "seat_service_item_id": None,
    }

    plan = {"is_renewable": False}

    model = bc.database.create(user=1, bag=bag, academy=1, currency=1, plan=plan, service_item=1, plan_offer=1)
    client.force_authenticate(user=model.user)

    url = reverse_lazy("payments:pay")
    data = {
        "token": "xdxdxdxdxdxdxdxdxdxd",
        "conversion_info": {"landing_url": "/home"},
    }
    response = client.post(url, data, format="json")

    json = response.json()
    expected = get_serializer(bc, model.currency, model.user, data={})

    assert json == expected
    assert response.status_code == status.HTTP_201_CREATED

    assert bc.database.list_of("payments.Bag") == [
        {
            **bc.format.to_dict(model.bag),
            "token": None,
            "status": "PAID",
            "expires_at": None,
        }
    ]
    assert bc.database.list_of("payments.Invoice") == [format_invoice_item()]
    assert bc.database.list_of("authenticate.UserSetting") == [
        format_user_setting({"lang": "en"}),
    ]

    bc.check.queryset_with_pks(model.bag.plans.all(), [1])
    bc.check.queryset_with_pks(model.bag.service_items.all(), [1])
    assert tasks.build_subscription.delay.call_args_list == []
    assert tasks.build_plan_financing.delay.call_args_list == []
    assert tasks.build_free_subscription.delay.call_args_list == [
        call(1, 1, conversion_info="{'landing_url': '/home'}")
    ]

    bc.check.calls(admissions_tasks.build_cohort_user.delay.call_args_list, [])
    bc.check.calls(admissions_tasks.build_profile_academy.delay.call_args_list, [call(1, 1)])
    bc.check.calls(
        activity_tasks.add_activity.delay.call_args_list,
        [
            call(1, "bag_created", related_type="payments.Bag", related_id=1),
            call(1, "checkout_completed", related_type="payments.Invoice", related_id=1),
        ],
    )


def test_with_chosen_period__amount_set(bc: Breathecode, client: APIClient):
    bag = {
        "token": "xdxdxdxdxdxdxdxdxdxd",
        "expires_at": UTC_NOW,
        "status": "CHECKING",
        "type": "BAG",
        **generate_amounts_by_time(),
        "seat_service_item_id": None,
    }
    chosen_period = random.choice(["MONTH", "QUARTER", "HALF", "YEAR"])
    amount = get_amount_per_period(chosen_period, bag)

    plan = {"is_renewable": False}

    model = bc.database.create(user=1, bag=bag, academy=1, currency=1, plan=plan, service_item=1)
    client.force_authenticate(user=model.user)

    url = reverse_lazy("payments:pay")
    data = {
        "token": "xdxdxdxdxdxdxdxdxdxd",
        "chosen_period": chosen_period,
    }
    response = client.post(url, data, format="json")

    json = response.json()
    expected = get_serializer(bc, model.currency, model.user, data={"amount": amount})

    assert json == expected
    assert response.status_code == status.HTTP_201_CREATED

    assert bc.database.list_of("payments.Bag") == [
        {
            **bc.format.to_dict(model.bag),
            "token": None,
            "status": "PAID",
            "expires_at": None,
            "chosen_period": chosen_period,
            "is_recurrent": True,
        }
    ]
    assert bc.database.list_of("payments.Invoice") == [
        format_invoice_item(
            {
                "amount": amount,
                "stripe_id": "1",
            }
        ),
    ]
    assert bc.database.list_of("authenticate.UserSetting") == [
        format_user_setting({"lang": "en"}),
    ]

    bc.check.queryset_with_pks(model.bag.plans.all(), [1])
    bc.check.queryset_with_pks(model.bag.service_items.all(), [1])
    assert tasks.build_subscription.delay.call_args_list == [call(1, 1, conversion_info="")]
    assert tasks.build_plan_financing.delay.call_args_list == []
    assert tasks.build_free_subscription.delay.call_args_list == []

    bc.check.calls(admissions_tasks.build_cohort_user.delay.call_args_list, [])
    bc.check.calls(admissions_tasks.build_profile_academy.delay.call_args_list, [call(1, 1)])
    bc.check.calls(
        activity_tasks.add_activity.delay.call_args_list,
        [
            call(1, "bag_created", related_type="payments.Bag", related_id=1),
            call(1, "checkout_completed", related_type="payments.Invoice", related_id=1),
        ],
    )


def test_with_chosen_period__amount_set_with_conversion_info(bc: Breathecode, client: APIClient):
    bag = {
        "token": "xdxdxdxdxdxdxdxdxdxd",
        "expires_at": UTC_NOW,
        "status": "CHECKING",
        "type": "BAG",
        **generate_amounts_by_time(),
        "seat_service_item_id": None,
    }
    chosen_period = random.choice(["MONTH", "QUARTER", "HALF", "YEAR"])
    amount = get_amount_per_period(chosen_period, bag)

    plan = {"is_renewable": False}

    model = bc.database.create(user=1, bag=bag, academy=1, currency=1, plan=plan, service_item=1)
    client.force_authenticate(user=model.user)

    url = reverse_lazy("payments:pay")
    data = {
        "token": "xdxdxdxdxdxdxdxdxdxd",
        "chosen_period": chosen_period,
        "conversion_info": {"landing_url": "/home"},
    }
    response = client.post(url, data, format="json")

    json = response.json()
    expected = get_serializer(bc, model.currency, model.user, data={"amount": amount})

    assert json == expected
    assert response.status_code == status.HTTP_201_CREATED

    assert bc.database.list_of("payments.Bag") == [
        {
            **bc.format.to_dict(model.bag),
            "token": None,
            "status": "PAID",
            "expires_at": None,
            "chosen_period": chosen_period,
            "is_recurrent": True,
        }
    ]
    assert bc.database.list_of("payments.Invoice") == [
        format_invoice_item(
            {
                "amount": amount,
                "stripe_id": "1",
            }
        ),
    ]
    assert bc.database.list_of("authenticate.UserSetting") == [
        format_user_setting({"lang": "en"}),
    ]

    bc.check.queryset_with_pks(model.bag.plans.all(), [1])
    bc.check.queryset_with_pks(model.bag.service_items.all(), [1])
    assert tasks.build_subscription.delay.call_args_list == [call(1, 1, conversion_info="{'landing_url': '/home'}")]
    assert tasks.build_plan_financing.delay.call_args_list == []
    assert tasks.build_free_subscription.delay.call_args_list == []

    bc.check.calls(admissions_tasks.build_cohort_user.delay.call_args_list, [])
    bc.check.calls(admissions_tasks.build_profile_academy.delay.call_args_list, [call(1, 1)])
    bc.check.calls(
        activity_tasks.add_activity.delay.call_args_list,
        [
            call(1, "bag_created", related_type="payments.Bag", related_id=1),
            call(1, "checkout_completed", related_type="payments.Invoice", related_id=1),
        ],
    )


def test_with_chosen_period__amount_set_with_conversion_info_with_wrong_fields(bc: Breathecode, client: APIClient):
    bag = {
        "token": "xdxdxdxdxdxdxdxdxdxd",
        "expires_at": UTC_NOW,
        "status": "CHECKING",
        "type": "BAG",
        **generate_amounts_by_time(),
        "seat_service_item_id": None,
    }
    chosen_period = random.choice(["MONTH", "QUARTER", "HALF", "YEAR"])
    amount = get_amount_per_period(chosen_period, bag)

    plan = {"is_renewable": False}

    model = bc.database.create(user=1, bag=bag, academy=1, currency=1, plan=plan, service_item=1)
    client.force_authenticate(user=model.user)

    url = reverse_lazy("payments:pay")
    data = {
        "token": "xdxdxdxdxdxdxdxdxdxd",
        "chosen_period": chosen_period,
        "conversion_info": {"pepe": "/home"},
    }
    response = client.post(url, data, format="json")

    json = response.json()
    expected = {"detail": "conversion-info-invalid-key", "status_code": 400}

    assert json == expected
    assert response.status_code == status.HTTP_400_BAD_REQUEST

    assert bc.database.list_of("payments.Bag") == [
        {
            **bc.format.to_dict(model.bag),
        }
    ]
    assert bc.database.list_of("payments.Invoice") == []
    assert bc.database.list_of("authenticate.UserSetting") == [
        format_user_setting({"lang": "en"}),
    ]

    bc.check.queryset_with_pks(model.bag.plans.all(), [1])
    bc.check.queryset_with_pks(model.bag.service_items.all(), [1])
    assert tasks.build_subscription.delay.call_args_list == []
    assert tasks.build_plan_financing.delay.call_args_list == []
    assert tasks.build_free_subscription.delay.call_args_list == []

    bc.check.calls(admissions_tasks.build_cohort_user.delay.call_args_list, [])
    bc.check.calls(admissions_tasks.build_profile_academy.delay.call_args_list, [])
    bc.check.calls(
        activity_tasks.add_activity.delay.call_args_list,
        [
            call(1, "bag_created", related_type="payments.Bag", related_id=1),
        ],
    )


def test_installments_not_found(bc: Breathecode, client: APIClient):
    bag = {
        "token": "xdxdxdxdxdxdxdxdxdxd",
        "expires_at": UTC_NOW,
        "status": "CHECKING",
        "type": "BAG",
        **generate_amounts_by_time(),
        "seat_service_item_id": None,
    }
    chosen_period = random.choice(["MONTH", "QUARTER", "HALF", "YEAR"])
    amount = get_amount_per_period(chosen_period, bag)

    plan = {"is_renewable": False}

    model = bc.database.create(user=1, bag=bag, academy=1, currency=1, plan=plan, service_item=1)
    client.force_authenticate(user=model.user)

    url = reverse_lazy("payments:pay")
    data = {
        "token": "xdxdxdxdxdxdxdxdxdxd",
        "how_many_installments": random.randint(1, 12),
    }
    response = client.post(url, data, format="json")

    json = response.json()
    expected = {"detail": "invalid-bag-configured-by-installments", "status_code": 500}

    assert json == expected
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    assert bc.database.list_of("payments.Bag") == [
        {
            **bc.format.to_dict(model.bag),
        }
    ]
    assert bc.database.list_of("payments.Invoice") == []
    assert bc.database.list_of("authenticate.UserSetting") == [
        format_user_setting({"lang": "en"}),
    ]

    bc.check.queryset_with_pks(model.bag.plans.all(), [1])
    bc.check.queryset_with_pks(model.bag.service_items.all(), [1])
    assert tasks.build_subscription.delay.call_args_list == []
    assert tasks.build_plan_financing.delay.call_args_list == []
    assert tasks.build_free_subscription.delay.call_args_list == []

    bc.check.calls(admissions_tasks.build_cohort_user.delay.call_args_list, [])
    bc.check.calls(admissions_tasks.build_profile_academy.delay.call_args_list, [])
    bc.check.calls(
        activity_tasks.add_activity.delay.call_args_list,
        [
            call(1, "bag_created", related_type="payments.Bag", related_id=1),
        ],
    )


def test_with_installments(bc: Breathecode, client: APIClient):
    how_many_installments = random.randint(1, 12)
    charge = random.random() * 99 + 1
    bag = {
        "token": "xdxdxdxdxdxdxdxdxdxd",
        "expires_at": UTC_NOW,
        "status": "CHECKING",
        "type": "BAG",
        **generate_amounts_by_time(),
        "seat_service_item_id": None,
    }
    financing_option = {
        "monthly_price": charge,
        "how_many_months": how_many_installments,
    }
    plan = {"is_renewable": False}

    model = bc.database.create(
        user=1,
        bag=bag,
        academy=1,
        currency=1,
        plan=plan,
        service_item=1,
        financing_option=financing_option,
    )
    client.force_authenticate(user=model.user)

    url = reverse_lazy("payments:pay")
    data = {
        "token": "xdxdxdxdxdxdxdxdxdxd",
        "how_many_installments": how_many_installments,
    }
    response = client.post(url, data, format="json")

    json = response.json()
    expected = get_serializer(bc, model.currency, model.user, data={"amount": charge})

    assert json == expected
    assert response.status_code == status.HTTP_201_CREATED

    assert bc.database.list_of("payments.Bag") == [
        {
            **bc.format.to_dict(model.bag),
            "token": None,
            "status": "PAID",
            #  'chosen_period': 'NO_SET',
            "expires_at": None,
            "how_many_installments": how_many_installments,
            "is_recurrent": True,
        }
    ]
    assert bc.database.list_of("payments.Invoice") == [
        format_invoice_item(
            {
                "amount": charge,
                "stripe_id": "1",
            }
        ),
    ]
    assert bc.database.list_of("authenticate.UserSetting") == [
        format_user_setting({"lang": "en"}),
    ]

    bc.check.queryset_with_pks(model.bag.plans.all(), [1])
    bc.check.queryset_with_pks(model.bag.service_items.all(), [1])
    assert tasks.build_subscription.delay.call_args_list == []
    assert tasks.build_plan_financing.delay.call_args_list == [
        call(1, 1, conversion_info=""),
    ]
    assert tasks.build_free_subscription.delay.call_args_list == []

    bc.check.calls(admissions_tasks.build_cohort_user.delay.call_args_list, [])
    bc.check.calls(admissions_tasks.build_profile_academy.delay.call_args_list, [call(1, 1)])
    bc.check.calls(
        activity_tasks.add_activity.delay.call_args_list,
        [
            call(1, "bag_created", related_type="payments.Bag", related_id=1),
            call(1, "checkout_completed", related_type="payments.Invoice", related_id=1),
        ],
    )


def test_with_installments_with_conversion_info(bc: Breathecode, client: APIClient):
    how_many_installments = random.randint(1, 12)
    charge = random.random() * 99 + 1
    bag = {
        "token": "xdxdxdxdxdxdxdxdxdxd",
        "expires_at": UTC_NOW,
        "status": "CHECKING",
        "type": "BAG",
        **generate_amounts_by_time(),
        "seat_service_item_id": None,
    }
    financing_option = {
        "monthly_price": charge,
        "how_many_months": how_many_installments,
    }
    plan = {"is_renewable": False}

    model = bc.database.create(
        user=1,
        bag=bag,
        academy=1,
        currency=1,
        plan=plan,
        service_item=1,
        financing_option=financing_option,
    )
    client.force_authenticate(user=model.user)

    url = reverse_lazy("payments:pay")
    data = {
        "token": "xdxdxdxdxdxdxdxdxdxd",
        "how_many_installments": how_many_installments,
        "conversion_info": {"landing_url": "/home"},
    }
    response = client.post(url, data, format="json")

    json = response.json()
    expected = get_serializer(bc, model.currency, model.user, data={"amount": charge})

    assert json == expected
    assert response.status_code == status.HTTP_201_CREATED

    assert bc.database.list_of("payments.Bag") == [
        {
            **bc.format.to_dict(model.bag),
            "token": None,
            "status": "PAID",
            #  'chosen_period': 'NO_SET',
            "expires_at": None,
            "how_many_installments": how_many_installments,
            "is_recurrent": True,
        }
    ]
    assert bc.database.list_of("payments.Invoice") == [
        format_invoice_item(
            {
                "amount": charge,
                "stripe_id": "1",
            }
        ),
    ]
    assert bc.database.list_of("authenticate.UserSetting") == [
        format_user_setting({"lang": "en"}),
    ]

    bc.check.queryset_with_pks(model.bag.plans.all(), [1])
    bc.check.queryset_with_pks(model.bag.service_items.all(), [1])
    assert tasks.build_subscription.delay.call_args_list == []
    assert tasks.build_plan_financing.delay.call_args_list == [call(1, 1, conversion_info="{'landing_url': '/home'}")]
    assert tasks.build_free_subscription.delay.call_args_list == []

    bc.check.calls(admissions_tasks.build_cohort_user.delay.call_args_list, [])
    bc.check.calls(admissions_tasks.build_profile_academy.delay.call_args_list, [call(1, 1)])
    bc.check.calls(
        activity_tasks.add_activity.delay.call_args_list,
        [
            call(1, "bag_created", related_type="payments.Bag", related_id=1),
            call(1, "checkout_completed", related_type="payments.Invoice", related_id=1),
        ],
    )


def test_coupons__with_installments(bc: Breathecode, client: APIClient):
    how_many_installments = random.randint(1, 12)
    charge = random.random() * 50 + 50
    bag = {
        "token": "xdxdxdxdxdxdxdxdxdxd",
        "expires_at": UTC_NOW,
        "status": "CHECKING",
        "type": "BAG",
        **generate_amounts_by_time(),
        "seat_service_item_id": None,
    }
    financing_option = {
        "monthly_price": charge,
        "how_many_months": how_many_installments,
    }
    plan = {"is_renewable": False}
    random_percent = random.random() * 0.3
    discount1 = random.random() * 20
    discount2 = random.random() * 10
    coupons = [
        {
            "discount_type": "PERCENT_OFF",
            "discount_value": random_percent,
            "offered_at": None,
            "expires_at": None,
        },
        {
            "discount_type": "FIXED_PRICE",
            "discount_value": discount1,
            "offered_at": None,
            "expires_at": None,
        },
        {
            "discount_type": "HAGGLING",
            "discount_value": discount2,
            "offered_at": None,
            "expires_at": None,
        },
    ]
    random.shuffle(coupons)

    model = bc.database.create(
        user=1,
        bag=bag,
        coupon=coupons,
        academy=1,
        currency=1,
        plan=plan,
        service_item=1,
        financing_option=financing_option,
    )
    client.force_authenticate(user=model.user)

    url = reverse_lazy("payments:pay")
    data = {
        "token": "xdxdxdxdxdxdxdxdxdxd",
        "how_many_installments": how_many_installments,
    }
    response = client.post(url, data, format="json")

    json = response.json()
    total = charge - (charge * random_percent) - discount1 - discount2
    expected = get_serializer(bc, model.currency, model.user, coupons=model.coupon, data={"amount": total})

    # handle tiny floating point differences
    assert math.isclose(json["amount"], total, rel_tol=1e-12, abs_tol=1e-12)
    expected["amount"] = json["amount"]
    assert json == expected
    assert response.status_code == status.HTTP_201_CREATED

    assert bc.database.list_of("payments.Bag") == [
        {
            **bc.format.to_dict(model.bag),
            "token": None,
            "status": "PAID",
            #  'chosen_period': 'NO_SET',
            "expires_at": None,
            "how_many_installments": how_many_installments,
            "is_recurrent": True,
        }
    ]
    assert bc.database.list_of("payments.Invoice") == [
        format_invoice_item(
            {
                "amount": total,
                "stripe_id": "1",
            }
        ),
    ]
    assert bc.database.list_of("authenticate.UserSetting") == [
        format_user_setting({"lang": "en"}),
    ]

    bc.check.queryset_with_pks(model.bag.plans.all(), [1])
    bc.check.queryset_with_pks(model.bag.service_items.all(), [1])
    assert tasks.build_subscription.delay.call_args_list == []
    assert tasks.build_plan_financing.delay.call_args_list == [call(1, 1, conversion_info="")]
    assert tasks.build_free_subscription.delay.call_args_list == []

    bc.check.calls(admissions_tasks.build_cohort_user.delay.call_args_list, [])
    bc.check.calls(admissions_tasks.build_profile_academy.delay.call_args_list, [call(1, 1)])
    bc.check.calls(
        activity_tasks.add_activity.delay.call_args_list,
        [
            call(1, "bag_created", related_type="payments.Bag", related_id=1),
            call(1, "checkout_completed", related_type="payments.Invoice", related_id=1),
        ],
    )


def test_coupons__with_chosen_period__amount_set(bc: Breathecode, client: APIClient):
    bag = {
        "token": "xdxdxdxdxdxdxdxdxdxd",
        "expires_at": UTC_NOW,
        "status": "CHECKING",
        "type": "BAG",
        **generate_amounts_by_time(over_50=True),
        "seat_service_item_id": None,
    }
    chosen_period = random.choice(["MONTH", "QUARTER", "HALF", "YEAR"])
    amount = get_amount_per_period(chosen_period, bag)

    plan = {"is_renewable": False}
    random_percent = random.random() * 0.3
    discount1 = random.random() * 20
    discount2 = random.random() * 10
    coupons = [
        {
            "discount_type": "PERCENT_OFF",
            "discount_value": random_percent,
            "offered_at": None,
            "expires_at": None,
        },
        {
            "discount_type": "FIXED_PRICE",
            "discount_value": discount1,
            "offered_at": None,
            "expires_at": None,
        },
        {
            "discount_type": "HAGGLING",
            "discount_value": discount2,
            "offered_at": None,
            "expires_at": None,
        },
    ]
    random.shuffle(coupons)

    model = bc.database.create(user=1, bag=bag, academy=1, currency=1, plan=plan, service_item=1, coupon=coupons)
    client.force_authenticate(user=model.user)

    url = reverse_lazy("payments:pay")
    data = {
        "token": "xdxdxdxdxdxdxdxdxdxd",
        "chosen_period": chosen_period,
    }
    response = client.post(url, data, format="json")

    json = response.json()
    total = amount - (amount * random_percent) - discount1 - discount2
    expected = get_serializer(bc, model.currency, model.user, coupons=model.coupon, data={"amount": total})

    assert json == expected
    assert response.status_code == status.HTTP_201_CREATED

    assert bc.database.list_of("payments.Bag") == [
        {
            **bc.format.to_dict(model.bag),
            "token": None,
            "status": "PAID",
            "expires_at": None,
            "chosen_period": chosen_period,
            "is_recurrent": True,
        }
    ]
    assert bc.database.list_of("payments.Invoice") == [
        format_invoice_item(
            {
                "amount": total,
                "stripe_id": "1",
            }
        ),
    ]
    assert bc.database.list_of("authenticate.UserSetting") == [
        format_user_setting({"lang": "en"}),
    ]

    bc.check.queryset_with_pks(model.bag.plans.all(), [1])
    bc.check.queryset_with_pks(model.bag.service_items.all(), [1])
    assert tasks.build_subscription.delay.call_args_list == [call(1, 1, conversion_info="")]
    assert tasks.build_plan_financing.delay.call_args_list == []
    assert tasks.build_free_subscription.delay.call_args_list == []

    bc.check.calls(admissions_tasks.build_cohort_user.delay.call_args_list, [])
    bc.check.calls(admissions_tasks.build_profile_academy.delay.call_args_list, [call(1, 1)])
    bc.check.calls(
        activity_tasks.add_activity.delay.call_args_list,
        [
            call(1, "bag_created", related_type="payments.Bag", related_id=1),
            call(1, "checkout_completed", related_type="payments.Invoice", related_id=1),
        ],
    )


def test_coupons__with_chosen_period__amount_set_with_conversion_info(bc: Breathecode, client: APIClient):
    bag = {
        "token": "xdxdxdxdxdxdxdxdxdxd",
        "expires_at": UTC_NOW,
        "status": "CHECKING",
        "type": "BAG",
        **generate_amounts_by_time(over_50=True),
        "seat_service_item_id": None,
    }
    chosen_period = random.choice(["MONTH", "QUARTER", "HALF", "YEAR"])
    amount = get_amount_per_period(chosen_period, bag)

    plan = {"is_renewable": False}
    random_percent = random.random() * 0.3
    discount1 = random.random() * 20
    discount2 = random.random() * 10
    coupons = [
        {
            "discount_type": "PERCENT_OFF",
            "discount_value": random_percent,
            "offered_at": None,
            "expires_at": None,
        },
        {
            "discount_type": "FIXED_PRICE",
            "discount_value": discount1,
            "offered_at": None,
            "expires_at": None,
        },
        {
            "discount_type": "HAGGLING",
            "discount_value": discount2,
            "offered_at": None,
            "expires_at": None,
        },
    ]
    random.shuffle(coupons)

    model = bc.database.create(user=1, bag=bag, academy=1, currency=1, plan=plan, service_item=1, coupon=coupons)
    client.force_authenticate(user=model.user)

    url = reverse_lazy("payments:pay")
    data = {
        "token": "xdxdxdxdxdxdxdxdxdxd",
        "chosen_period": chosen_period,
        "conversion_info": {"landing_url": "/home"},
    }
    response = client.post(url, data, format="json")

    json = response.json()
    total = amount - (amount * random_percent) - discount1 - discount2
    expected = get_serializer(bc, model.currency, model.user, coupons=model.coupon, data={"amount": total})

    assert json == expected
    assert response.status_code == status.HTTP_201_CREATED

    assert bc.database.list_of("payments.Bag") == [
        {
            **bc.format.to_dict(model.bag),
            "token": None,
            "status": "PAID",
            "expires_at": None,
            "chosen_period": chosen_period,
            "is_recurrent": True,
        }
    ]
    assert bc.database.list_of("payments.Invoice") == [
        format_invoice_item(
            {
                "amount": total,
                "stripe_id": "1",
            }
        ),
    ]
    assert bc.database.list_of("authenticate.UserSetting") == [
        format_user_setting({"lang": "en"}),
    ]

    bc.check.queryset_with_pks(model.bag.plans.all(), [1])
    bc.check.queryset_with_pks(model.bag.service_items.all(), [1])
    assert tasks.build_subscription.delay.call_args_list == [call(1, 1, conversion_info="{'landing_url': '/home'}")]
    assert tasks.build_plan_financing.delay.call_args_list == []
    assert tasks.build_free_subscription.delay.call_args_list == []

    bc.check.calls(admissions_tasks.build_cohort_user.delay.call_args_list, [])
    bc.check.calls(admissions_tasks.build_profile_academy.delay.call_args_list, [call(1, 1)])
    bc.check.calls(
        activity_tasks.add_activity.delay.call_args_list,
        [
            call(1, "bag_created", related_type="payments.Bag", related_id=1),
            call(1, "checkout_completed", related_type="payments.Invoice", related_id=1),
        ],
    )


def test_pay_for_plan_financing_with_country_code_and_ratio(
    bc: Breathecode, client: APIClient, monkeypatch, fake, utc_now
):
    # Mock necessary stripe functions
    stripe_charge_id = fake.slug()
    stripe_customer_id = fake.slug()
    monkeypatch.setattr("stripe.Charge.create", MagicMock(return_value={"id": stripe_charge_id}))
    monkeypatch.setattr("stripe.Customer.create", MagicMock(return_value={"id": stripe_customer_id}))

    country_code = "VE"
    ratio = 0.8
    monthly_price = 100.0
    final_price = monthly_price * ratio

    # Setup models
    plan = {
        "is_renewable": False,
        "price_per_month": 0,  # Not used directly for financing
        "time_of_life": 6,
        "time_of_life_unit": "MONTH",
        "status": "ACTIVE",  # Ensure the plan is active
    }
    financing_option = {
        "monthly_price": monthly_price,
        "how_many_months": 6,
        "pricing_ratio_exceptions": {
            country_code.lower(): {
                "ratio": ratio,
                "currency": "USD",  # Optional currency override for display, charge uses bag currency
            }
        },
    }
    bag = {
        "status": "CHECKING",
        "type": "BAG",
        "how_many_installments": 6,
        "token": fake.slug(),
        "country_code": country_code,  # Set country code on the bag
        "expires_at": UTC_NOW + timedelta(minutes=10),  # Set expires_at
        "seat_service_item_id": None,
    }
    currency = {"code": "USD"}
    model = bc.database.create(
        user=1,
        plan=plan,
        financing_option=financing_option,
        bag=bag,
        currency=currency,
        academy=1,  # Ensure academy exists for PlanFinancing
    )

    # Explicitly link bag to plan and coupons
    model.bag.plans.add(model.plan)
    # Link financing option to plan
    model.plan.financing_options.add(model.financing_option)
    model.bag.save()
    model.plan.save()

    client.force_authenticate(user=model.user)
    url = reverse_lazy("payments:pay")
    data = {
        "token": model.bag.token,
        "how_many_installments": model.bag.how_many_installments,
    }
    response = client.post(url, data, format="json")

    # Assertions
    json = response.json()
    # Get the created invoice ID from the successful response or DB query if needed
    # Assuming invoice ID is 1 based on previous tests
    invoice_id = 1
    invoice = bc.database.get("payments.Invoice", invoice_id, dict=False)

    # If the request failed, invoice will be None, handle this case
    if invoice is None:
        assert response.status_code != status.HTTP_201_CREATED, "Invoice not found, but status was 201"
        # Add more specific assertions about the error response if needed
        expected_error = {"detail": "not-found-or-without-checking", "status_code": 404}  # Example expected error
        assert json == expected_error
        assert response.status_code == status.HTTP_404_NOT_FOUND
        return  # Exit test early as invoice doesn't exist

    # Proceed with assertions if invoice exists
    expected_amount = math.ceil(final_price)

    expected_invoice_data = {
        "academy_id": 1,
        "amount": expected_amount,  # Use calculated amount
        "bag_id": model.bag.id,
        "currency_id": model.currency.id,
        "id": invoice_id,
        "paid_at": invoice.paid_at,  # Use actual paid_at from created invoice
        "status": "FULFILLED",
        "stripe_id": stripe_charge_id,
        "user_id": model.user.id,
        "refund_stripe_id": None,
        "refunded_at": None,
        "externally_managed": False,
        "payment_method_id": None,
        "proof_id": None,
    }

    expected_serializer = get_serializer(bc, model.currency, model.user, data={})
    expected_serializer["paid_at"] = bc.datetime.to_iso_string(invoice.paid_at)
    expected_serializer["amount"] = expected_amount

    assert json == expected_serializer
    assert response.status_code == status.HTTP_201_CREATED

    # Verify DB state
    assert bc.database.list_of("payments.Bag") == [
        {
            **bc.format.to_dict(model.bag),
            "status": "PAID",
            "token": None,
            "expires_at": None,
            "is_recurrent": True,  # Should be true for installments
            "currency_id": model.currency.id,  # Verify currency is saved
        }
    ]
    db_invoice = bc.database.get("payments.Invoice", invoice_id, dict=True)
    db_invoice["amount"] = math.ceil(db_invoice["amount"])
    expected_invoice_data["paid_at"] = invoice.paid_at  # Keep datetime for DB comparison
    assert db_invoice == expected_invoice_data

    # Verify stripe call
    assert stripe.Charge.create.call_args_list == [
        call(
            customer=stripe_customer_id,
            amount=int(expected_amount),
            currency=model.currency.code.lower(),
            description="",
        )
    ]
    user = model.user
    name = f"{user.first_name} {user.last_name}"
    assert stripe.Customer.create.call_args_list == [
        call(email=user.email, name=name),
    ]

    # Verify task call
    assert tasks.build_plan_financing.delay.call_args_list == [call(1, 1, conversion_info="")]

    # Verify activity calls
    bc.check.calls(
        activity_tasks.add_activity.delay.call_args_list,
        [
            call(model.user.id, "bag_created", related_type="payments.Bag", related_id=1),
            call(model.user.id, "checkout_completed", related_type="payments.Invoice", related_id=1),
        ],
    )


def test_pay_for_plan_financing_with_country_code_and_price_override(
    bc: Breathecode, client: APIClient, monkeypatch, fake
):
    """
    Test that the pay endpoint correctly charges the overridden price from
    pricing_ratio_exceptions for a specific country when financing.
    """
    # Mock necessary stripe functions
    stripe_charge_id = fake.slug()
    stripe_customer_id = fake.slug()
    monkeypatch.setattr("stripe.Charge.create", MagicMock(return_value={"id": stripe_charge_id}))
    monkeypatch.setattr("stripe.Customer.create", MagicMock(return_value={"id": stripe_customer_id}))

    country_code = "VE"
    override_price = 50.0  # Direct price override
    monthly_price = 100.0  # Original price
    how_many_installments = 6

    # Setup models
    plan = {
        "is_renewable": False,
        "price_per_month": 0,  # Not used directly for financing
        "time_of_life": 6,
        "time_of_life_unit": "MONTH",
        "status": "ACTIVE",
    }
    financing_option = {
        "monthly_price": monthly_price,
        "how_many_months": how_many_installments,
        "pricing_ratio_exceptions": {
            country_code.lower(): {
                "price": override_price,
                "currency": "USD",
            }
        },
    }
    bag = {
        "status": "CHECKING",
        "type": "BAG",
        "how_many_installments": how_many_installments,
        "token": fake.slug(),
        "country_code": country_code,  # Set country code on the bag
        "expires_at": UTC_NOW + timedelta(minutes=10),  # Set expires_at
        "seat_service_item_id": None,
    }
    currency = {"code": "USD"}
    model = bc.database.create(
        user=1,
        plan=plan,
        financing_option=financing_option,
        bag=bag,
        currency=currency,
        academy=1,
    )

    # Explicitly link bag to plan and coupons
    model.bag.plans.add(model.plan)
    # Link financing option to plan
    model.plan.financing_options.add(model.financing_option)
    model.bag.save()
    model.plan.save()

    client.force_authenticate(user=model.user)
    url = reverse_lazy("payments:pay")
    data = {
        "token": model.bag.token,
        "how_many_installments": model.bag.how_many_installments,
    }
    response = client.post(url, data, format="json")

    # Assertions
    json = response.json()
    invoice_id = 1
    invoice = bc.database.get("payments.Invoice", invoice_id, dict=False)

    assert invoice is not None, "Invoice was not created"

    expected_amount = math.ceil(override_price)

    expected_invoice_data = {
        "academy_id": 1,
        "amount": expected_amount,
        "bag_id": model.bag.id,
        "currency_id": model.currency.id,
        "id": invoice_id,
        "paid_at": invoice.paid_at,
        "status": "FULFILLED",
        "stripe_id": stripe_charge_id,
        "user_id": model.user.id,
        "refund_stripe_id": None,
        "refunded_at": None,
        "externally_managed": False,
        "payment_method_id": None,
        "proof_id": None,
    }

    expected_serializer = get_serializer(bc, model.currency, model.user, data={})
    expected_serializer["paid_at"] = bc.datetime.to_iso_string(invoice.paid_at)
    expected_serializer["amount"] = expected_amount

    assert json == expected_serializer
    assert response.status_code == status.HTTP_201_CREATED

    # Verify DB state
    db_bag = bc.database.get("payments.Bag", 1, dict=True)
    assert db_bag["status"] == "PAID"
    assert db_bag["token"] is None
    assert db_bag["country_code"] == country_code
    assert db_bag["how_many_installments"] == how_many_installments
    # Explanation should be empty because direct price was used
    assert db_bag["pricing_ratio_explanation"] == {"plans": [], "service_items": []}

    db_invoice = bc.database.get("payments.Invoice", invoice_id, dict=True)
    db_invoice["amount"] = math.ceil(db_invoice["amount"])
    expected_invoice_data["paid_at"] = invoice.paid_at
    assert db_invoice == expected_invoice_data

    # Verify stripe call
    assert stripe.Charge.create.call_args_list == [
        call(
            customer=stripe_customer_id,
            amount=int(expected_amount),
            currency=model.currency.code.lower(),
            description="",
        )
    ]
    user = model.user
    name = f"{user.first_name} {user.last_name}"
    assert stripe.Customer.create.call_args_list == [
        call(email=user.email, name=name),
    ]

    # Verify task call
    assert tasks.build_plan_financing.delay.call_args_list == [
        call(1, 1, conversion_info=""),
    ]

    # Verify activity calls
    bc.check.calls(
        activity_tasks.add_activity.delay.call_args_list,
        [
            call(model.user.id, "bag_created", related_type="payments.Bag", related_id=1),
            call(model.user.id, "checkout_completed", related_type="payments.Invoice", related_id=1),
        ],
    )
