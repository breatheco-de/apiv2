"""Functional tests for paying a PER_SEAT plan end-to-end.

This script verifies preview, payment, subscription creation, and basic
consumable behavior for a PER_SEAT plan using the public API.
It assumes FTT_* environment variables are set and polls while
asynchronous processes complete.
"""

from __future__ import annotations

import os
import requests
import time

from ..utils import assert_env_vars
from .. import api


PER_SEAT_PLAN = "4geeks-premium"
PER_TEAM_PLAN = "hack-30-machines-in-30-days"
ASSET_SLUG = "brute-forcelab-lumi"

TOKEN1 = os.getenv("FTT_USER_TOKEN1", "")
TOKEN2 = os.getenv("FTT_USER_TOKEN2", "")
academy = os.getenv("FTT_ACADEMY", "")
pay_request = api.pay(token=TOKEN1, academy=academy)
put_card_request = api.card(token=TOKEN1, academy=academy)
checking_request = api.checking(token=TOKEN1, academy=academy)
get_user1_consumables_request = api.consumables(token=TOKEN1)
get_user2_consumables_request = api.consumables(token=TOKEN2)
get_subscription_request = api.subscriptions(token=TOKEN1, academy=academy)
get_plan_request = api.plan(token=TOKEN1, academy=academy)
get_seats_request = api.seats(token=TOKEN1)
get_seat_request = api.seat(token=TOKEN1)
get_user1_me_request = api.user_me(token=TOKEN1)
get_user2_me_request = api.user_me(token=TOKEN2)
put_seat_request = api.add_seat(token=TOKEN1)
delete_seat_request = api.delete_seat(token=TOKEN1)
get_user1_asset_request = api.get_asset(token=TOKEN1, academy=academy)
get_user2_asset_request = api.get_asset(token=TOKEN2, academy=academy)


def get_subscription_id(slug: str) -> int | None:
    """Return the subscription id for the given plan slug or None if not found."""
    res = get_subscription_request()
    assert_response(res)
    x = res.json()
    for subs in x["subscriptions"]:
        for plan in subs["plans"]:
            if plan["slug"] == slug:
                return subs["id"]


def setup() -> None:
    """Validate environment and PER_SEAT plan preconditions before tests run."""
    assert_env_vars(
        ["FTT_API_URL", "FTT_USER_TOKEN1", "FTT_USER_TOKEN2", "FTT_ACADEMY", "FTT_ACADEMY_SLUG"]
    )  # required
    base = os.environ["FTT_API_URL"].rstrip("/")

    sub_id = get_subscription_id(PER_SEAT_PLAN)
    assert (
        sub_id is None
    ), f"Subscription to `{PER_SEAT_PLAN}` found, delete it on {base}/admin/payments/subscription/{sub_id}/delete/"

    plan = get_plan_request(PER_SEAT_PLAN)
    assert_response(plan)
    json_plan = plan.json()
    assert any(
        [x for x in json_plan.get("service_items", []) if x.get("is_team_allowed")]
    ), "No team allowed service item found"
    assert "consumption_strategy" in json_plan, "consumption_strategy not found in response"
    assert json_plan.get("consumption_strategy") == "PER_SEAT", "consumption_strategy is not PER_SEAT"

    assert "seat_service_price" in json_plan, "seat_service_price not found in response"
    assert json_plan.get("seat_service_price") is not None, "seat_service_price is None"
    assert any(
        [x for x in json_plan.get("service_items", []) if x["service"]["consumer"] == "READ_LESSON"]
    ), f"No read lesson service item found in this plan {json_plan.get('slug')}"
    return {"plan_id": json_plan.get("id")}


def assert_response(res: requests.Response) -> None:
    """Assert JSON content-type and a successful (2xx/3xx) status code."""
    assert "application/json" in (
        res.headers.get("Content-Type") or ""
    ), f"{res.request.method} {res.request.url} {res.request.body} Content-Type is not application/json"
    assert (
        200 <= res.status_code < 400
    ), f"{res.request.method} {res.request.url} {res.request.body} request failed at {res.request.url} with status {res.status_code}, {res.text}"


def test_checking_works_properly(plan_id: int) -> None:
    """Preview the plan and assert seat_service_item is absent in preview."""

    data = {"type": "PREVIEW", "plans": [plan_id]}
    res = checking_request(data)
    assert_response(res)

    json_res = res.json()

    assert "seat_service_item" in json_res, "seat_service_item not found in response"
    assert json_res.get("seat_service_item") is None, "seat_service_item is not None"

    bag_token = json_res.get("token")
    return {"bag_token": bag_token}


def test_set_the_payment_card(**ctx) -> None:
    """Attach a valid test payment card to the account."""
    data = {"card_number": "4242424242424242", "cvc": "123", "exp_month": "12", "exp_year": "2035"}

    res = put_card_request(data)
    assert_response(res)


def test_pay_a_plan(bag_token: str, **ctx) -> None:
    """Pay the plan and wait for the subscription to be created."""
    data = {"token": bag_token, "chosen_period": "MONTH"}
    res = pay_request(data)
    assert_response(res)

    json_res = res.json()

    assert "amount" in json_res, "amount not found in response"
    assert json_res.get("amount") is not None, "amount is None"
    assert json_res.get("amount") > 0, "amount is not greater than 0"

    attempts = 0
    while attempts < 10:
        time.sleep(10)
        if subscription_id := get_subscription_id(PER_SEAT_PLAN):
            return {"subscription_id": subscription_id}
        attempts += 1

    assert 0, "Subscription was not created"


def get_owner_consumables(subscription_id: int) -> requests.Response:
    """Return consumables issued to the owner for the given subscription id."""
    res = get_user1_consumables_request()
    assert_response(res)
    json_res = res.json()
    consumables = []
    for x in json_res.values():
        for y in x:
            for item in y["items"]:
                if item["subscription"] == subscription_id:
                    consumables.append(item)
    return consumables


def test_owner_consumables(subscription_id: int, **ctx):
    """Assert owner consumables exist and at least one is owner-level (no seat)."""
    attempts = 0
    while attempts < 20:
        time.sleep(10)
        consumables = get_owner_consumables(subscription_id)
        if consumables:
            assert all([x["user"] is not None for x in consumables]), "Consumables were issued without user"
            assert any([x["subscription_seat"] is None for x in consumables]), "Owner consumables were not issued"
            return
        attempts += 1

    assert 0, "Consumables were not created"


def test_owner_can_read_lesson(**ctx):
    """Verify the owner can access a lesson protected by a consumable."""
    res = get_user1_asset_request(ASSET_SLUG)
    assert_response(res)
