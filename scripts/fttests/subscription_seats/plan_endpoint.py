from __future__ import annotations

import os
import requests

from ..utils import assert_env_vars, build_headers, print_section


def setup() -> None:
    print("[fttests] Setting up smoke test...")
    assert_env_vars(["FTT_API_URL", "FTT_OWNER_TOKEN", "FTT_ACADEMY"])  # required


def plan_request() -> requests.Response:
    base_url = os.environ["FTT_API_URL"].rstrip("/")
    owner_token = os.getenv("FTT_OWNER_TOKEN", "")
    academy = os.getenv("FTT_ACADEMY", "")
    path = "/v1/payments/plan/prework-usa"
    url = f"{base_url}{path}"
    headers = build_headers(authorization=f"Token {owner_token}", accept="application/json", academy=academy)
    res = requests.get(url, headers=headers)
    return res


def test_plan_with_seat_service_price() -> None:
    """Basic reachability smoke test for the API health endpoint."""

    print_section("subscription_seats: smoke test")

    res = plan_request()
    assert "application/json" in (res.headers.get("Content-Type") or ""), "Content-Type is not application/json"
    assert 200 <= res.status_code < 400, f"Plan request failed at {res.request.url} with status {res.status_code}"

    json_res = res.json()

    assert "seat_service_price" in json_res, "seat_service_price not found in response"
    assert json_res.get("seat_service_price") is not None, "seat_service_price is None"
