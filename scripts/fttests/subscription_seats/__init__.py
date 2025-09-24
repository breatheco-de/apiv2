"""Functional tests for the Subscription Seats feature.

Exported contract:
    - check_dependencies() -> None
    - run() -> None

Environment variables:
    - FTT_BASE_URL      (required) e.g. https://apiv2-dev.herokuapp.com
    - FTT_API_TOKEN     (optional) bearer token if needed for protected endpoints
    - FTT_HEALTH_PATH   (optional) path to a health endpoint, defaults to '/'
    - FTT_SEATS_LIST_PATH (optional) path to list seats, e.g. '/v1/subscriptions/seats'
"""

from __future__ import annotations

import json
import os
import urllib.parse

from ..utils import assert_env_vars, build_headers, http_request, print_section


REQUIRED_ENV = [
    "FTT_BASE_URL",
]


def check_dependencies() -> None:
    """Verify required environment variables and basic URL sanity."""
    assert_env_vars(REQUIRED_ENV)

    base_url = os.environ["FTT_BASE_URL"].strip()
    parsed = urllib.parse.urlparse(base_url)
    assert parsed.scheme in {"http", "https"}, "FTT_BASE_URL must include scheme http(s)"
    assert parsed.netloc, "FTT_BASE_URL must include a hostname"


def run() -> None:
    """Run a minimal smoke test against the API.

    This is intentionally simple; extend with real subscription seats scenarios later.
    """
    print_section("subscription_seats: smoke test")

    base_url = os.environ["FTT_BASE_URL"].rstrip("/")
    health_path = os.getenv("FTT_HEALTH_PATH", "/")
    path = health_path if health_path.startswith("/") else f"/{health_path}"
    url = f"{base_url}{path}"

    headers = build_headers(token_env="FTT_API_TOKEN")
    status, resp_headers, body = http_request("GET", url, headers=headers)

    # Basic assertion: endpoint is reachable and returns 2xx or 3xx
    assert 200 <= status < 400, f"Health check failed at {url} with status {status}"

    # Placeholder for future, e.g., create seat, allocate, list, delete, etc.
    # Add concrete endpoints and assertions here as the feature matures.

    # Optional: list seats endpoint if provided
    _maybe_test_list_seats()


def _maybe_test_list_seats() -> None:
    """If FTT_SEATS_LIST_PATH is set, perform a GET and assert reachability.

    This serves as a first real endpoint touch-point for subscription seats.
    """
    path = os.getenv("FTT_SEATS_LIST_PATH")
    if not path:
        print("[fttests] Skipping list seats test (FTT_SEATS_LIST_PATH not set)")
        return

    print_section("subscription_seats: list seats")

    base_url = os.environ["FTT_BASE_URL"].rstrip("/")
    url = f"{base_url}{path if path.startswith('/') else '/' + path}"
    headers = build_headers(token_env="FTT_API_TOKEN")
    status, resp_headers, body = http_request("GET", url, headers=headers)

    assert 200 <= status < 400, f"List seats failed at {url} with status {status}"

    # If JSON, try to parse for debug purposes (no schema enforced here)
    content_type = (resp_headers.get("Content-Type") or "").lower()
    if "application/json" in content_type:
        try:
            payload = json.loads(body.decode("utf-8")) if body else None
            # Non-failing lightweight sanity: payload should be dict or list
            assert isinstance(payload, (dict, list)), "Expected JSON object or array"
        except Exception as exc:  # noqa: BLE001
            # Treat invalid JSON as a failure for this test
            raise AssertionError(f"Invalid JSON response from {url}: {exc}") from exc
