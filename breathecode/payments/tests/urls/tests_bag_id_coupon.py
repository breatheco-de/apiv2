import re
from datetime import UTC, datetime
from typing import Any

import pytest
from django.db.models.query import QuerySet
from django.urls import reverse_lazy
from rest_framework import status

from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode
from capyc.rest_framework.pytest import fixtures as rfx


def queryset_with_pks(query: Any, pks: list[int]) -> None:
    """
    Check if the queryset have the following primary keys.

    Usage:

    ```py
    from breathecode.admissions.models import Cohort, Academy

    self.bc.database.create(cohort=1)

    collection = []
    queryset = Cohort.objects.filter()

    # pass because the QuerySet has the primary keys 1
    self.bc.check.queryset_with_pks(queryset, [1])  # 🟢

    # fail because the QuerySet has the primary keys 1 but the second argument is empty
    self.bc.check.queryset_with_pks(queryset, [])  # 🔴
    ```
    """

    assert isinstance(query, QuerySet), "The first argument is not a QuerySet"

    assert [x.pk for x in query] == pks


@pytest.fixture(autouse=True)
def setup(db):
    yield


def db_bag(data={}):
    return {
        "academy_id": 0,
        "amount_per_half": 0.0,
        "amount_per_month": 0.0,
        "amount_per_quarter": 0.0,
        "amount_per_year": 0.0,
        "chosen_period": "NO_SET",
        "currency_id": 0,
        "expires_at": None,
        "how_many_installments": 0,
        "id": 0,
        "is_recurrent": False,
        "status": "CHECKING",
        "token": None,
        "type": "BAG",
        "user_id": 0,
        "was_delivered": False,
        **data,
    }


def plan_serializer(plan, data={}):
    return {
        "service_items": [],
        "financing_options": [],
        "slug": plan.slug,
        "status": plan.status,
        "time_of_life": plan.time_of_life,
        "time_of_life_unit": plan.time_of_life_unit,
        "trial_duration": plan.trial_duration,
        "trial_duration_unit": plan.trial_duration_unit,
        "has_available_cohorts": bool(plan.cohort_set),
        **data,
    }


def to_iso(date: datetime) -> str:
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


def put_serializer(bag, plans=[], coupons=[], data={}):
    return {
        "id": bag.id,
        "amount_per_month": bag.amount_per_month,
        "amount_per_quarter": bag.amount_per_quarter,
        "amount_per_half": bag.amount_per_half,
        "amount_per_year": bag.amount_per_year,
        "expires_at": bag.expires_at,
        "is_recurrent": bag.is_recurrent,
        "plans": [plan_serializer(plan) for plan in plans],
        "service_items": [],
        "status": bag.status,
        "token": bag.token,
        "type": bag.type,
        "was_delivered": bag.was_delivered,
        "coupons": [format_coupon(x) for x in coupons],
        **data,
    }


@pytest.mark.parametrize("plan_pk", [None, ""])
def test_no_auth(bc: Breathecode, client: rfx.Client, plan_pk):
    url = reverse_lazy("payments:bag_id_coupon", kwargs={"bag_id": 1})
    if plan_pk is not None:
        url += f"?plan={plan_pk}"

    response = client.put(url)

    json = response.json()
    expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}

    assert json == expected
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert bc.database.list_of("payments.Plan") == []
    assert bc.database.list_of("payments.Coupon") == []
    assert bc.database.list_of("payments.Bag") == []


@pytest.mark.parametrize("plan_pk", [None, ""])
def test_missing_plan(bc: Breathecode, client: rfx.Client, plan_pk):
    model = bc.database.create(user=1)
    client.force_authenticate(user=model.user)

    url = reverse_lazy("payments:bag_id_coupon", kwargs={"bag_id": 1})
    if plan_pk is not None:
        url += f"?plan={plan_pk}"

    response = client.put(url)

    json = response.json()
    expected = {"detail": "missing-plan", "status_code": 404}

    assert json == expected
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert bc.database.list_of("payments.Plan") == []
    assert bc.database.list_of("payments.Coupon") == []
    assert bc.database.list_of("payments.Bag") == []


@pytest.mark.parametrize("plan_pk", ["my-plan", 1])
def test_plan_not_found(bc: Breathecode, client: rfx.Client, plan_pk):
    model = bc.database.create(user=1)
    client.force_authenticate(user=model.user)

    url = reverse_lazy("payments:bag_id_coupon", kwargs={"bag_id": 1})
    if plan_pk is not None:
        url += f"?plan={plan_pk}"

    response = client.put(url)

    json = response.json()
    expected = {"detail": "plan-not-found", "status_code": 404}

    assert json == expected
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert bc.database.list_of("payments.Plan") == []
    assert bc.database.list_of("payments.Coupon") == []
    assert bc.database.list_of("payments.Bag") == []


@pytest.mark.parametrize("plan_pk", ["my-plan", 1])
def test_no_bag(bc: Breathecode, client: rfx.Client, plan_pk):
    plan = {
        "is_renewable": False,
    }
    if isinstance(plan_pk, str):
        plan["slug"] = plan_pk

    model = bc.database.create(plan=plan, user=1)
    client.force_authenticate(user=model.user)

    url = reverse_lazy("payments:bag_id_coupon", kwargs={"bag_id": 1})
    url += f"?plan={plan_pk}&coupons=coupon1,coupon2"

    response = client.put(url)

    json = response.json()
    expected = {
        "detail": "bag-not-found",
        "status_code": 404,
    }

    assert json == expected
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert bc.database.list_of("payments.Plan") == [bc.format.to_dict(model.plan)]
    assert bc.database.list_of("payments.Coupon") == []
    assert bc.database.list_of("payments.Bag") == []


@pytest.mark.parametrize("plan_pk", ["my-plan", 1])
@pytest.mark.parametrize(
    "bag_type, coupons",
    [
        ("BAG", 0),
        ("BAG", [{"slug": slug, "auto": False, "discount_value": 1} for slug in ["coupon3", "coupon4"]]),
        ("PREVIEW", [{"slug": slug, "auto": False, "discount_value": 1} for slug in ["coupon3", "coupon4"]]),
    ],
)
def test_plan_found__coupons_not_found(bc: Breathecode, client: rfx.Client, bag_type, plan_pk, coupons):
    plan = {
        "is_renewable": False,
    }
    if isinstance(plan_pk, str):
        plan["slug"] = plan_pk

    model = bc.database.create(plan=plan, coupon=coupons, user=1, bag={"status": "CHECKING", "type": bag_type})
    client.force_authenticate(user=model.user)

    url = reverse_lazy("payments:bag_id_coupon", kwargs={"bag_id": 1})
    url += f"?plan={plan_pk}&coupons=coupon1,coupon2"

    response = client.put(url)

    json = response.json()
    expected = put_serializer(bag=model.bag, plans=[model.plan], coupons=[])

    assert json == expected
    assert response.status_code == status.HTTP_200_OK
    assert bc.database.list_of("payments.Plan") == [bc.format.to_dict(model.plan)]
    if coupons:
        assert bc.database.list_of("payments.Coupon") == bc.format.to_dict(model.coupon)
    else:
        assert bc.database.list_of("payments.Coupon") == []

    assert bc.database.list_of("payments.Bag") == [bc.format.to_dict(model.bag)]
    queryset_with_pks(model.bag.coupons.all(), [])


@pytest.mark.parametrize("plan_pk", ["my-plan", 1])
@pytest.mark.parametrize(
    "bag_type, max, coupons",
    [
        ("BAG", 2, [{"slug": slug, "auto": True, "discount_value": 1} for slug in ["coupon3", "coupon4"]]),
        ("PREVIEW", 1, [{"slug": slug, "auto": False, "discount_value": 1} for slug in ["coupon1", "coupon2"]]),
        (
            "BAG",
            3,
            [{"slug": slug, "auto": True, "discount_value": 1} for slug in ["coupon3", "coupon4"]]
            + [{"slug": slug, "auto": False, "discount_value": 1} for slug in ["coupon1", "coupon2"]],
        ),
    ],
)
def test_plan_found__coupons_found(bc: Breathecode, client: rfx.Client, plan_pk, max, coupons, bag_type):
    plan = {
        "is_renewable": False,
    }
    if isinstance(plan_pk, str):
        plan["slug"] = plan_pk

    model = bc.database.create(plan=plan, coupon=coupons, user=1, bag={"status": "CHECKING", "type": bag_type})
    client.force_authenticate(user=model.user)

    url = reverse_lazy("payments:bag_id_coupon", kwargs={"bag_id": 1})
    url += f"?plan={plan_pk}&coupons=coupon1,coupon2"

    response = client.put(url)

    json = response.json()
    expected = put_serializer(bag=model.bag, plans=[model.plan], coupons=model.coupon[0:max])

    assert json == expected
    assert response.status_code == status.HTTP_200_OK
    assert bc.database.list_of("payments.Plan") == [bc.format.to_dict(model.plan)]
    assert bc.database.list_of("payments.Coupon") == bc.format.to_dict(model.coupon)
    assert bc.database.list_of("payments.Bag") == [bc.format.to_dict(model.bag)]
    queryset_with_pks(model.bag.coupons.all(), [n + 1 for n in range(max)])
