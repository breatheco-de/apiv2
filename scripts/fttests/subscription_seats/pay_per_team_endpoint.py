from __future__ import annotations

import os
import requests
import time
from typing import TypedDict

from ..utils import assert_env_vars
from .. import api


PER_SEAT_PLAN = "4geeks-premium"
PER_TEAM_PLAN = "hack-30-machines-in-30-days"
ASSET_SLUG = "brute-forcelab-lumi"

# we switch the tokens to do not collide with pay_per_seat_endpoint
TOKEN1 = os.getenv("FTT_USER_TOKEN2", "")
TOKEN2 = os.getenv("FTT_USER_TOKEN1", "")

academy = os.getenv("FTT_ACADEMY", "")
pay_request = api.pay(token=TOKEN1, academy=academy)
put_card_request = api.card(token=TOKEN1, academy=academy)
checking_request = api.checking(token=TOKEN1, academy=academy)
get_user1_consumables_request = api.consumables(token=TOKEN1)
get_user2_consumables_request = api.consumables(token=TOKEN2)
get_billing_team_request = api.billing_team(token=TOKEN1)
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
    res = get_subscription_request()
    assert_response(res)
    x = res.json()
    for subs in x["subscriptions"]:
        for plan in subs["plans"]:
            if plan["slug"] == slug:
                return subs["id"]


def setup() -> None:
    assert_env_vars(
        ["FTT_API_URL", "FTT_USER_TOKEN1", "FTT_USER_TOKEN2", "FTT_ACADEMY", "FTT_ACADEMY_SLUG"]
    )  # required
    base = os.environ["FTT_API_URL"].rstrip("/")

    sub_id = get_subscription_id(PER_TEAM_PLAN)
    assert (
        sub_id is None
    ), f"Subscription to `{PER_TEAM_PLAN}` found, delete it on {base}/admin/payments/subscription/{sub_id}/delete/"

    plan = get_plan_request(PER_TEAM_PLAN)
    assert_response(plan)
    json_plan = plan.json()

    assert any(
        [x for x in json_plan.get("service_items", []) if x.get("is_team_allowed")]
    ), "No team allowed service item found"
    assert any(
        [x for x in json_plan.get("service_items", []) if x.get("is_team_allowed") is False]
    ), "No service item for subscription owner found"
    assert "consumption_strategy" in json_plan, "consumption_strategy not found in response"
    assert json_plan.get("consumption_strategy") == "PER_TEAM", "consumption_strategy is not PER_TEAM"

    assert "seat_service_price" in json_plan, "seat_service_price not found in response"
    assert json_plan.get("seat_service_price") is not None, "seat_service_price is None"
    assert any(
        [x for x in json_plan.get("service_items", []) if x["service"]["consumer"] == "READ_LESSON"]
    ), f"No read lesson service item found in this plan {json_plan.get('slug')}"
    return {"plan_id": json_plan.get("id")}


def assert_response(res: requests.Response) -> None:
    assert "application/json" in (
        res.headers.get("Content-Type") or ""
    ), f"{res.request.method} {res.request.url} {res.request.body} Content-Type is not application/json"
    assert (
        200 <= res.status_code < 400
    ), f"{res.request.method} {res.request.url} {res.request.body} request failed at {res.request.url} with status {res.status_code}, {res.text}"


def test_checking_works_properly_with_team_seats(plan_id: int) -> None:
    """Buy a plan with seats."""

    data = {"team_seats": 3, "type": "PREVIEW", "plans": [plan_id]}
    res = checking_request(data)
    assert_response(res)

    json_res = res.json()

    assert "seat_service_item" in json_res, "seat_service_item not found in response"
    assert json_res.get("seat_service_item") is not None, "seat_service_item is None"

    bag_token = json_res.get("token")
    return {"bag_token": bag_token, "team_seats": 3}


def test_set_the_payment_card(**ctx) -> None:
    data = {"card_number": "4242424242424242", "cvc": "123", "exp_month": "12", "exp_year": "2035"}

    res = put_card_request(data)
    assert_response(res)


def test_pay_a_plan_with_seats(bag_token: str, **ctx) -> None:
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
        if subscription_id := get_subscription_id(PER_TEAM_PLAN):
            return {"subscription_id": subscription_id}
        attempts += 1

    assert 0, "Subscription was not created"


def get_owner_consumables(subscription_id: int) -> requests.Response:
    res = get_user1_consumables_request()
    assert_response(res)
    json_res = res.json()
    consumables = []
    for x in json_res.values():
        for y in x:
            for item in y["items"]:
                if item["subscription"] == subscription_id:
                    consumables.append(item)
    from pprint import pprint

    pprint(consumables)
    return consumables


def test_owner_can_read_lesson(**ctx):
    res = get_user1_asset_request(ASSET_SLUG)
    assert_response(res)


def test_owner_consumables(subscription_id: int, **ctx):
    attempts = 0
    while attempts < 20:
        time.sleep(10)
        consumables = get_owner_consumables(subscription_id)
        if consumables:
            assert all([x["user"] is not None for x in consumables]), "Consumables were issued without user"
            assert any([x["subscription_seat"] is None for x in consumables]), "Owner consumables were not issued"
            assert any(
                [x["subscription_seat"] is not None for x in consumables]
            ), "Owner seat consumables were not issued"
            return
        attempts += 1

    assert 0, "Consumables were not created"


def test_billing_team_exists(subscription_id: int, team_seats: int, **ctx):
    res = get_billing_team_request(subscription_id)
    assert_response(res)
    json_res = res.json()
    assert json_res.get("seats_limit") == team_seats, "billing_team seats_limit is not equal to team_seats"


def test_owner_seat_exists(subscription_id: int, **ctx):
    res = get_user1_me_request()
    assert_response(res)
    json_res = res.json()

    user_id = json_res.get("id")
    user_email = json_res.get("email")

    res = get_seats_request(subscription_id)
    assert_response(res)
    json_res = res.json()

    assert any(
        [x["user"] == user_id and x["email"] == user_email for x in json_res]
    ), "owner's seat not found in response"


def test_add_seat(subscription_id: int, **ctx):
    user_email = "lord@valomero.com"

    data = {
        "add_seats": [
            {
                "email": user_email,
                "seat_multiplier": 1,
                "first_name": "Lord",
                "last_name": "Valomero",
            }
        ]
    }
    res = put_seat_request(subscription_id, data)
    assert_response(res)

    res = get_seats_request(subscription_id)
    assert_response(res)
    json_res = res.json()

    assert any(
        [x["user"] is None and x["email"] == user_email for x in json_res]
    ), "Lord valomero's seat not found in response"

    # we couldn't check the consumables of the invitee because they need to join to 4geeks


def test_replace_seat(subscription_id: int, **ctx):
    user_email = "lord@valomero.com"

    res = get_user2_me_request()
    assert_response(res)
    json_res = res.json()

    from_email = user_email
    user_id = json_res.get("id")
    to_email = json_res.get("email")

    data = {
        "replace_seats": [
            {
                "from_email": from_email,
                "to_email": to_email,
                "seat_multiplier": 1,
                "first_name": "Lord",
                "last_name": "Valomero",
            }
        ]
    }
    res = put_seat_request(subscription_id, data)
    assert_response(res)

    res = get_seats_request(subscription_id)
    assert_response(res)
    json_res = res.json()

    assert any([x["user"] == user_id and x["email"] == to_email for x in json_res]), "Seat replacement failed"
    return {
        "seats": [
            {
                "id": x["id"],
                "user": x["user"],
                "email": x["email"],
            }
            for x in json_res
        ]
    }


def get_user2_consumables(subscription_id: int) -> requests.Response:
    res = get_user2_consumables_request()
    assert_response(res)
    json_res = res.json()
    consumables = []
    for x in json_res.values():
        for y in x:
            for item in y["items"]:
                if item["subscription"] == subscription_id:
                    consumables.append(item)
    return consumables


def test_user2_consumables(subscription_id: int, **ctx):
    attempts = 0
    while attempts < 20:
        time.sleep(10)
        consumables = get_user2_consumables(subscription_id)
        if consumables:
            assert all([x["user"] is not None for x in consumables]), "Consumables were issued without user"
            assert all(
                [x["subscription_seat"] is not None for x in consumables]
            ), "Consumables related to user2 were issued without subscription seat"
            return consumables
        attempts += 1

    assert 0, "Consumables were not created"


def test_user2_can_read_lesson(**ctx):
    res = get_user2_asset_request(ASSET_SLUG)
    assert_response(res)


class Seat(TypedDict):
    id: int
    user: int
    email: str


def test_delete_user2_seat(subscription_id: int, seats: list[Seat], **ctx):
    res = delete_seat_request(subscription_id, seats[1].get("id"))
    assert res.status_code == 204, f"Delete seat failed, {res.text}"


def test_user2_consumables_after_seat_deletion(subscription_id: int, **ctx):
    consumables = get_user2_consumables(subscription_id)
    assert len(consumables) == 0, "Consumables were not deleted"
