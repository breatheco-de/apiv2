from __future__ import annotations

import os
from typing import Dict
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


def test_smoke_health() -> None:
    """Basic reachability smoke test for the API health endpoint."""

    print_section("subscription_seats: smoke test")

    res = plan_request()
    assert "application/json" in (res.headers.get("Content-Type") or ""), "Content-Type is not application/json"
    assert 200 <= res.status_code < 400, f"Plan request failed at {res.request.url} with status {res.status_code}"

    json_res = res.json()

    assert "seat_service_price" in json_res, "seat_service_price not found in response"
    assert json_res.get("seat_service_price") is not None, "seat_service_price is None"

    print()
    print()
    print()
    print()
    print()
    print(res.status_code, res.text)

    data = {"seats": 3, "type": "PREVIEW"}
    res = checking_request(data)

    print()
    print()
    print()
    print()
    print()
    print()
    print(res.status_code, res.text)

    assert 200 <= res.status_code < 400, f"Health check failed at {res.request.url} with status {res.status_code}"


# def test_list_seats_if_configured() -> None:
#     """If FTT_SEATS_LIST_PATH is set, perform a GET and assert reachability and basic JSON shape."""
#     assert_env_vars(["FTT_BASE_URL"])  # required for building the URL

#     path = os.getenv("FTT_SEATS_LIST_PATH")
#     if not path:
#         # not a failure: test is a no-op when not configured
#         return

#     print_section("subscription_seats: list seats")

#     base_url = os.environ["FTT_BASE_URL"].rstrip("/")
#     url = f"{base_url}{path if path.startswith('/') else '/' + path}"
#     headers = build_headers(token_env="FTT_API_TOKEN")
#     status, resp_headers, body = http_request("GET", url, headers=headers)

#     assert 200 <= status < 400, f"List seats failed at {url} with status {status}"

#     # If JSON, try to parse for debug purposes (no schema enforced here)
#     content_type = (resp_headers.get("Content-Type") or "").lower()
#     if "application/json" in content_type:
#         try:
#             payload = json.loads(body.decode("utf-8")) if body else None
#             # Non-failing lightweight sanity: payload should be dict or list
#             assert isinstance(payload, (dict, list)), "Expected JSON object or array"
#         except Exception as exc:  # noqa: BLE001
#             # Treat invalid JSON as a failure for this test
#             raise AssertionError(f"Invalid JSON response from {url}: {exc}") from exc
