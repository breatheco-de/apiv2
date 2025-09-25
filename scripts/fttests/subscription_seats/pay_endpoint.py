from __future__ import annotations

import os
from typing import Dict
import requests
import time

from ..utils import assert_env_vars, build_headers


def subscription_request() -> requests.Response:
    base_url = os.environ["FTT_API_URL"].rstrip("/")
    owner_token = os.getenv("FTT_OWNER_TOKEN", "")
    academy = os.getenv("FTT_ACADEMY", "")
    path = "/v1/payments/me/subscription"
    url = f"{base_url}{path}"
    headers = build_headers(authorization=f"Token {owner_token}", accept="application/json", academy=academy)
    res = requests.get(url, headers=headers)
    return res


def get_subscription_id(slug: str) -> int | None:
    res = subscription_request()
    assert_response(res)
    x = res.json()
    for subs in x["subscriptions"]:
        for plan in subs["plans"]:
            if plan["slug"] == slug:
                return subs["id"]


def setup() -> None:
    print("[fttests] Setting up smoke test...")
    assert_env_vars(["FTT_API_URL", "FTT_OWNER_TOKEN", "FTT_ACADEMY", "FTT_ACADEMY_SLUG"])  # required
    base = os.environ["FTT_API_URL"].rstrip("/")

    sub_id = get_subscription_id("4geeks-premium")
    assert (
        sub_id is None
    ), f"Subscription `4geeks-premium` found, delete it on {base}/admin/payments/subscription/{sub_id}/change/"


def assert_response(res: requests.Response) -> None:
    assert "application/json" in (
        res.headers.get("Content-Type") or ""
    ), f"{res.request.method} {res.request.url} Content-Type is not application/json"
    assert (
        200 <= res.status_code < 400
    ), f"{res.request.method} {res.request.url} request failed at {res.request.url} with status {res.status_code}, {res.text[:40]}"


def plan_request(slug) -> requests.Response:
    base_url = os.environ["FTT_API_URL"].rstrip("/")
    owner_token = os.getenv("FTT_OWNER_TOKEN", "")
    academy = os.getenv("FTT_ACADEMY", "")
    path = f"/v1/payments/plan/{slug}"
    url = f"{base_url}{path}"
    headers = build_headers(authorization=f"Token {owner_token}", accept="application/json", academy=academy)
    res = requests.get(url, headers=headers)
    return res


def checking_request(data: Dict[str, str]) -> requests.Response:
    base_url = os.environ["FTT_API_URL"].rstrip("/")
    owner_token = os.getenv("FTT_OWNER_TOKEN", "")
    academy = os.getenv("FTT_ACADEMY", "")
    path = "/v1/payments/checking"
    url = f"{base_url}{path}"
    data["academy"] = academy
    headers = build_headers(authorization=f"Token {owner_token}", accept="application/json")
    res = requests.put(url, headers=headers, json=data)
    return res


def card_request(data: Dict[str, str]) -> requests.Response:
    base_url = os.environ["FTT_API_URL"].rstrip("/")
    owner_token = os.getenv("FTT_OWNER_TOKEN", "")
    academy = os.getenv("FTT_ACADEMY", "")
    academy_slug = os.getenv("FTT_ACADEMY_SLUG", "")
    path = "/v1/payments/card"
    url = f"{base_url}{path}"
    data["academy"] = academy_slug
    headers = build_headers(authorization=f"Token {owner_token}", accept="application/json", academy=academy)
    res = requests.post(url, headers=headers, json=data)
    return res


def pay_request(data: Dict[str, str]) -> requests.Response:
    base_url = os.environ["FTT_API_URL"].rstrip("/")
    owner_token = os.getenv("FTT_OWNER_TOKEN", "")
    academy = os.getenv("FTT_ACADEMY", "")
    path = "/v1/payments/pay"
    url = f"{base_url}{path}"
    data["academy"] = academy
    headers = build_headers(authorization=f"Token {owner_token}", accept="application/json")
    res = requests.post(url, headers=headers, json=data)
    return res


def test_plan_setup_with_seat_price() -> None:
    """Buy a plan with seats."""

    res = plan_request("4geeks-premium")
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
    return {"bag_token": bag_token}


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
        if get_subscription_id("4geeks-premium"):
            return
        attempts += 1

    assert 0, "Subscription was not created"
