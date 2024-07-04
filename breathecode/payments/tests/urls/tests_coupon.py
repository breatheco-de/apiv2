import pytest
from django.urls import reverse_lazy
from rest_framework import status

from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode
from capyc.rest_framework.pytest import fixtures as rfx


@pytest.fixture(autouse=True)
def setup(db):
    yield


def get_serializer(bc: Breathecode, coupon):
    return {
        "auto": coupon.auto,
        "discount_type": coupon.discount_type,
        "discount_value": coupon.discount_value,
        "expires_at": coupon.expires_at,
        "offered_at": bc.datetime.to_iso_string(coupon.offered_at),
        "referral_type": coupon.referral_type,
        "referral_value": coupon.referral_value,
        "slug": coupon.slug,
    }


@pytest.mark.parametrize("plan_pk", [None, ""])
def test_missing_plan(bc: Breathecode, client: rfx.Client, plan_pk):
    url = reverse_lazy("payments:coupon")
    if plan_pk is not None:
        url += f"?plan={plan_pk}"

    response = client.get(url)

    json = response.json()
    expected = {"detail": "missing-plan", "status_code": 404}

    assert json == expected
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert bc.database.list_of("payments.Plan") == []
    assert bc.database.list_of("payments.Coupon") == []


@pytest.mark.parametrize("plan_pk", ["my-plan", 1])
def test_plan_not_found(bc: Breathecode, client: rfx.Client, plan_pk):
    url = reverse_lazy("payments:coupon")
    if plan_pk is not None:
        url += f"?plan={plan_pk}"

    response = client.get(url)

    json = response.json()
    expected = {"detail": "plan-not-found", "status_code": 404}

    assert json == expected
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert bc.database.list_of("payments.Plan") == []
    assert bc.database.list_of("payments.Coupon") == []


@pytest.mark.parametrize("plan_pk", ["my-plan", 1])
@pytest.mark.parametrize(
    "coupons",
    [
        0,
        ([{"slug": slug, "auto": False, "discount_value": 1} for slug in ["coupon3", "coupon4"]]),
    ],
)
def test_plan_found__coupons_not_found(bc: Breathecode, client: rfx.Client, plan_pk, coupons):
    plan = {
        "is_renewable": False,
    }
    if isinstance(plan_pk, str):
        plan["slug"] = plan_pk

    model = bc.database.create(plan=plan, coupon=coupons)

    url = reverse_lazy("payments:coupon")
    url += f"?plan={plan_pk}&coupons=coupon1,coupon2"

    response = client.get(url)

    json = response.json()
    expected = []

    assert json == expected
    assert response.status_code == status.HTTP_200_OK
    assert bc.database.list_of("payments.Plan") == [bc.format.to_dict(model.plan)]
    if coupons:
        assert bc.database.list_of("payments.Coupon") == bc.format.to_dict(model.coupon)
    else:
        assert bc.database.list_of("payments.Coupon") == []


@pytest.mark.parametrize("plan_pk", ["my-plan", 1])
@pytest.mark.parametrize(
    "max, coupons",
    [
        (2, [{"slug": slug, "auto": True, "discount_value": 1} for slug in ["coupon3", "coupon4"]]),
        (1, [{"slug": slug, "auto": False, "discount_value": 1} for slug in ["coupon1", "coupon2"]]),
        (
            3,
            [{"slug": slug, "auto": True, "discount_value": 1} for slug in ["coupon3", "coupon4"]]
            + [{"slug": slug, "auto": False, "discount_value": 1} for slug in ["coupon1", "coupon2"]],
        ),
    ],
)
def test_plan_found__coupons_found(bc: Breathecode, client: rfx.Client, plan_pk, max, coupons):
    plan = {
        "is_renewable": False,
    }
    if isinstance(plan_pk, str):
        plan["slug"] = plan_pk

    model = bc.database.create(plan=plan, coupon=coupons)

    url = reverse_lazy("payments:coupon")
    url += f"?plan={plan_pk}&coupons=coupon1,coupon2"

    response = client.get(url)

    json = response.json()
    expected = [get_serializer(bc, coupon) for coupon in model.coupon[0:max]]

    assert json == expected
    assert response.status_code == status.HTTP_200_OK
    assert bc.database.list_of("payments.Plan") == [bc.format.to_dict(model.plan)]
    assert bc.database.list_of("payments.Coupon") == bc.format.to_dict(model.coupon)
