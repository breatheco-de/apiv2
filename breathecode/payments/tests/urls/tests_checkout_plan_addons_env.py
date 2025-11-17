import os

import pytest
from django.urls import reverse_lazy
from rest_framework import status
from rest_framework.test import APIClient

from breathecode.admissions.models import Academy, Country
from breathecode.payments.models import Coupon, Currency, FinancingOption, Plan
from django.contrib.auth.models import User


@pytest.mark.django_db
def test_checkout_with_plan_addons_env(client: APIClient):
    """
    Integration harness for checking + plan_addons + coupons.

    This test is driven by environment variables so you can quickly
    tweak amounts and see the backend behaviour without touching code.

    Required env vars (if any is missing, the test is skipped):
      - CHECKOUT_TEST_PLAN_PRICE_MONTH   (float, e.g. 100)
      - CHECKOUT_TEST_ADDON_PRICE_ONE_SHOT (float, e.g. 400)
      - CHECKOUT_TEST_DISCOUNT_VALUE    (float between 0 and 1, e.g. 0.5)
    """

    plan_price = os.getenv("CHECKOUT_TEST_PLAN_PRICE_MONTH")
    addon_price = os.getenv("CHECKOUT_TEST_ADDON_PRICE_ONE_SHOT")
    discount_value = os.getenv("CHECKOUT_TEST_DISCOUNT_VALUE")

    if plan_price is None or addon_price is None or discount_value is None:
        pytest.skip("Env vars CHECKOUT_TEST_PLAN_PRICE_MONTH, "
                    "CHECKOUT_TEST_ADDON_PRICE_ONE_SHOT and "
                    "CHECKOUT_TEST_DISCOUNT_VALUE must be set")

    plan_price = float(plan_price)
    addon_price = float(addon_price)
    discount_value = float(discount_value)

    # 1) Minimal data setup

    # currency and country
    currency = Currency.objects.create(code="USD", name="US Dollar", decimals=2)
    country = Country.objects.create(code="US", name="United States")
    country.currencies.add(currency)

    # academy
    academy = Academy.objects.create(name="Test Academy", slug="test-academy", main_currency=currency, country=country)

    # user
    user = User.objects.create_user(username="checkout-user", email="checkout@example.com", password="pass")
    client.force_authenticate(user=user)

    # main plan with monthly price
    main_plan = Plan.objects.create(
        slug="env-main-plan",
        title="Env Main Plan",
        owner=academy,
        price_per_month=plan_price,
        is_renewable=True,
    )

    # financing option for the main plan (just to keep model consistent if needed later)
    FinancingOption.objects.create(
        academy=academy,
        monthly_price=plan_price,
        how_many_months=1,
        currency=currency,
    )

    # addon plan (one-shot) with financing option how_many_months=1
    addon_plan = Plan.objects.create(
        slug="env-addon-plan",
        title="Env Addon Plan",
        owner=academy,
        is_renewable=False,
        time_of_life=1,
        time_of_life_unit="MONTH",
    )
    FinancingOption.objects.create(
        academy=academy,
        monthly_price=addon_price,
        how_many_months=1,
        currency=currency,
    )

    # wire addon to main plan
    main_plan.plan_addons.add(addon_plan)

    # coupon that only applies to the main plan
    coupon = Coupon.objects.create(
        slug="env-discount",
        discount_type=Coupon.Discount.PERCENT_OFF,
        discount_value=discount_value,
        referral_type=Coupon.Referral.NO_REFERRAL,
        referral_value=0,
    )
    coupon.plans.add(main_plan)

    # 2) Call checking endpoint with plan + addon + coupon

    url = reverse_lazy("payments:checking")
    body = {
        "type": "PREVIEW",
        "plans": [main_plan.slug],
        "plan_addons": [addon_plan.slug],
        "country_code": "US",
        "coupons": [coupon.slug],
        "academy": academy.slug,
    }

    response = client.put(url, body, format="json")

    assert response.status_code in (status.HTTP_200_OK, status.HTTP_201_CREATED)

    data = response.json()

    # 3) Basic expectations: structure

    assert "plans" in data
    assert "plan_addons" in data
    assert "amount_per_month" in data
    assert "discounted_amount_per_month" in data
    assert "plan_addons_amount" in data
    assert "discounted_plan_addons_amount" in data

    # We only check that discounted_amount_per_month is lower than amount_per_month
    # and that discounted_plan_addons_amount is <= plan_addons_amount
    # because the precise math is already covered by unit tests.

    assert data["amount_per_month"] == pytest.approx(plan_price)
    assert data["discounted_amount_per_month"] < data["amount_per_month"]

    assert data["plan_addons_amount"] == pytest.approx(addon_price)
    assert data["discounted_plan_addons_amount"] <= data["plan_addons_amount"]


