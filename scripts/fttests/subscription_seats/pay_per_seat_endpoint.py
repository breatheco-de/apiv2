from __future__ import annotations

import os
import requests
import time

from ..utils import assert_env_vars
from .. import api


PER_SEAT_PLAN = "4geeks-premium"
PER_TEAM_PLAN = "hack-30-machines-in-30-days"

TOKEN1 = os.getenv("FTT_USER_TOKEN1", "")
TOKEN2 = os.getenv("FTT_USER_TOKEN2", "")
academy = os.getenv("FTT_ACADEMY", "")
pay_request = api.pay(token=TOKEN1, academy=academy)
card_request = api.card(token=TOKEN1, academy=academy)
checking_request = api.checking(token=TOKEN1, academy=academy)
consumables_request = api.consumables(token=TOKEN1)
billing_team_request = api.billing_team(token=TOKEN1)
subscription_request = api.subscriptions(token=TOKEN1, academy=academy)
plan_request = api.plan(token=TOKEN1, academy=academy)
seats_request = api.seats(token=TOKEN1)
seat_request = api.seat(token=TOKEN1)
user1_me_request = api.user_me(token=TOKEN1)
user2_me_request = api.user_me(token=TOKEN2)
add_seat_request = api.add_seat(token=TOKEN1)


def get_subscription_id(slug: str) -> int | None:
    res = subscription_request()
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

    sub_id = get_subscription_id(PER_SEAT_PLAN)
    assert (
        sub_id is None
    ), f"Subscription to `{PER_SEAT_PLAN}` found, delete it on {base}/admin/payments/subscription/{sub_id}/delete/"

    plan = plan_request(PER_SEAT_PLAN)
    assert_response(plan)
    json_plan = plan.json()
    assert "consumption_strategy" in json_plan, "consumption_strategy not found in response"
    assert json_plan.get("consumption_strategy") == "PER_SEAT", "consumption_strategy is not PER_SEAT"


def assert_response(res: requests.Response) -> None:
    assert "application/json" in (
        res.headers.get("Content-Type") or ""
    ), f"{res.request.method} {res.request.url} {res.request.body} Content-Type is not application/json"
    assert (
        200 <= res.status_code < 400
    ), f"{res.request.method} {res.request.url} {res.request.body} request failed at {res.request.url} with status {res.status_code}, {res.text[:40]}"


def test_plan_setup_with_seat_price() -> None:
    """Buy a plan with seats."""

    res = plan_request(PER_SEAT_PLAN)
    assert_response(res)

    json_res = res.json()

    assert "seat_service_price" in json_res, "seat_service_price not found in response"
    assert json_res.get("seat_service_price") is not None, "seat_service_price is None"
    return {"plan_id": json_res.get("id")}


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

    res = card_request(data)
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
        if subscription_id := get_subscription_id(PER_SEAT_PLAN):
            return {"subscription_id": subscription_id}
        attempts += 1

    assert 0, "Subscription was not created"


def test_all_consumables(subscription_id: int, **ctx):
    attempts = 0
    while attempts < 10:
        time.sleep(10)
        consumables = get_consumables(subscription_id)
        if consumables:
            assert all([x["user"] is not None for x in consumables]), "Consumables were issued without user"
            assert all(
                [x["subscription_seat"] is None for x in consumables]
            ), "Consumables related to ownerwere issued with subscription seat"
            # assert all(
            #     [x["plan_financing"] is not None for x in consumables]
            # ), "Consumables were issued without plan financing"
            return consumables
        attempts += 1

    assert 0, "Consumables were not created"


def get_consumables(subscription_id: int) -> requests.Response:
    res = consumables_request()
    assert_response(res)
    json_res = res.json()
    consumables = []
    for x in json_res.values():
        for y in x:
            for item in y["items"]:
                if item["subscription"] == subscription_id:
                    consumables.append(item)
    return consumables


def test_billing_team_exists(subscription_id: int, team_seats: int, **ctx):
    res = billing_team_request(subscription_id)
    assert_response(res)
    json_res = res.json()
    assert json_res.get("seats_limit") == team_seats, "billing_team seats_limit is not equal to team_seats"


def test_owner_seat_exists(subscription_id: int, **ctx):
    res = user1_me_request()
    assert_response(res)
    json_res = res.json()

    user_id = json_res.get("id")
    user_email = json_res.get("email")

    res = seats_request(subscription_id)
    assert_response(res)
    json_res = res.json()

    assert any(
        [x["user"] == user_id and x["email"] == user_email for x in json_res]
    ), "owner's seat not found in response"


# def test_add_seat(subscription_id: int, **ctx):
#     user_email = "lord@valomero.com"

#     data = {
#         "add_seats": [
#             {
#                 "email": user_email,
#                 "seat_multiplier": 1,
#                 "first_name": "Lord",
#                 "last_name": "Valomero",
#             }
#         ]
#     }
#     res = add_seat_request(subscription_id, data)
#     assert_response(res)

#     res = seats_request(subscription_id)
#     assert_response(res)
#     json_res = res.json()

#     assert any(
#         [x["user"] is None and x["email"] == user_email for x in json_res]
#     ), "Lord valomero's seat not found in response"

#     res = user2_me_request()
#     assert_response(res)
#     json_res = res.json()

#     from_email = user_email
#     user_id = json_res.get("id")
#     to_email = json_res.get("email")

#     data = {
#         "replace_seats": [
#             {
#                 "from_email": from_email,
#                 "to_email": to_email,
#                 "seat_multiplier": 1,
#                 "first_name": "Lord",
#                 "last_name": "Valomero",
#             }
#         ]
#     }
#     res = add_seat_request(subscription_id, data)
#     assert_response(res)

#     res = seats_request(subscription_id)
#     assert_response(res)
#     json_res = res.json()

#     assert any([x["user"] == user_id and x["email"] == to_email for x in json_res]), "Seat replacement failed"
