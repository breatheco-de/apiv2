import requests
from .utils import build_headers
import os
from typing import Dict, Callable


def subscriptions(token: str, academy: str | int) -> Callable[[str, str], requests.Response]:
    def inner() -> requests.Response:
        nonlocal academy
        base_url = os.environ["FTT_API_URL"].rstrip("/")
        owner_token = token
        path = "/v1/payments/me/subscription"
        url = f"{base_url}{path}"
        headers = build_headers(authorization=f"Token {owner_token}", accept="application/json", academy=academy)
        res = requests.get(url, headers=headers)
        return res

    return inner


def plan(token: str, academy: str | int) -> Callable[[str, str], requests.Response]:
    def inner(slug) -> requests.Response:
        nonlocal academy
        base_url = os.environ["FTT_API_URL"].rstrip("/")
        owner_token = token
        path = f"/v1/payments/plan/{slug}"
        url = f"{base_url}{path}"
        headers = build_headers(authorization=f"Token {owner_token}", accept="application/json", academy=academy)
        res = requests.get(url, headers=headers)
        return res

    return inner


def checking(token: str, academy: str | int) -> Callable[[str, str], requests.Response]:
    def inner(data: Dict[str, str]) -> requests.Response:
        nonlocal academy
        base_url = os.environ["FTT_API_URL"].rstrip("/")
        owner_token = token
        path = "/v1/payments/checking"
        url = f"{base_url}{path}"
        data["academy"] = academy
        headers = build_headers(authorization=f"Token {owner_token}", accept="application/json")
        res = requests.put(url, headers=headers, json=data)
        return res

    return inner


def card(token: str, academy: str | int) -> Callable[[str, str], requests.Response]:
    def inner(data: Dict[str, str]) -> requests.Response:
        nonlocal academy

        base_url = os.environ["FTT_API_URL"].rstrip("/")
        owner_token = token
        path = "/v1/payments/card"
        url = f"{base_url}{path}"
        data["academy"] = int(academy) if isinstance(academy, str) and academy.isnumeric() else academy
        headers = build_headers(authorization=f"Token {owner_token}", accept="application/json", academy=academy)
        res = requests.post(url, headers=headers, json=data)
        return res

    return inner


def pay(token: str, academy: str | int) -> Callable[[str, str], requests.Response]:
    def inner(data: Dict[str, str]) -> requests.Response:
        base_url = os.environ["FTT_API_URL"].rstrip("/")
        owner_token = token
        path = "/v1/payments/pay"
        url = f"{base_url}{path}"
        data["academy"] = academy
        headers = build_headers(authorization=f"Token {owner_token}", accept="application/json")
        res = requests.post(url, headers=headers, json=data)
        return res

    return inner


def consumables(token: str) -> Callable[[str, str], requests.Response]:
    def inner() -> requests.Response:
        base_url = os.environ["FTT_API_URL"].rstrip("/")
        owner_token = token
        path = "/v1/payments/me/service/consumable"
        url = f"{base_url}{path}"
        headers = build_headers(authorization=f"Token {owner_token}", accept="application/json")
        res = requests.get(url, headers=headers)
        return res

    return inner


def billing_team(token: str) -> Callable[[str, str], requests.Response]:
    def inner(subscription_id: int) -> requests.Response:
        base_url = os.environ["FTT_API_URL"].rstrip("/")
        owner_token = token
        path = f"/v2/payments/subscription/{subscription_id}/billing-team"
        url = f"{base_url}{path}"
        headers = build_headers(authorization=f"Token {owner_token}", accept="application/json")
        res = requests.get(url, headers=headers)
        return res

    return inner


def seats(token: str) -> Callable[[str, str], requests.Response]:
    def inner(subscription_id: int) -> requests.Response:
        base_url = os.environ["FTT_API_URL"].rstrip("/")
        owner_token = token
        path = f"/v2/payments/subscription/{subscription_id}/billing-team/seat"
        url = f"{base_url}{path}"
        headers = build_headers(authorization=f"Token {owner_token}", accept="application/json")
        res = requests.get(url, headers=headers)
        return res

    return inner


def seat(token: str) -> Callable[[str, str], requests.Response]:
    def inner(subscription_id: int, seat_id: int) -> requests.Response:
        base_url = os.environ["FTT_API_URL"].rstrip("/")
        owner_token = token
        path = f"/v2/payments/subscription/{subscription_id}/billing-team/seat/{seat_id}"
        url = f"{base_url}{path}"
        headers = build_headers(authorization=f"Token {owner_token}", accept="application/json")
        res = requests.get(url, headers=headers)
        return res

    return inner


def user_me(token: str) -> Callable[[str, str], requests.Response]:
    def inner() -> requests.Response:
        base_url = os.environ["FTT_API_URL"].rstrip("/")
        owner_token = token
        path = "/v1/auth/user/me"
        url = f"{base_url}{path}"
        headers = build_headers(authorization=f"Token {owner_token}", accept="application/json")
        res = requests.get(url, headers=headers)
        return res

    return inner


def add_seat(token: str) -> Callable[[str, str], requests.Response]:
    def inner(subscription_id: int, data: Dict[str, str]) -> requests.Response:
        base_url = os.environ["FTT_API_URL"].rstrip("/")
        owner_token = token
        path = f"/v2/payments/subscription/{subscription_id}/billing-team/seat"
        url = f"{base_url}{path}"
        headers = build_headers(authorization=f"Token {owner_token}", accept="application/json")
        res = requests.put(url, headers=headers, json=data)
        return res

    return inner


def delete_seat(token: str) -> Callable[[str, str], requests.Response]:
    def inner(subscription_id: int, seat_id: int) -> requests.Response:
        base_url = os.environ["FTT_API_URL"].rstrip("/")
        owner_token = token
        path = f"/v2/payments/subscription/{subscription_id}/billing-team/seat/{seat_id}"
        url = f"{base_url}{path}"
        headers = build_headers(authorization=f"Token {owner_token}", accept="application/json")
        res = requests.delete(url, headers=headers)
        return res

    return inner


def get_asset(token: str, academy: str | int) -> Callable[[str, str], requests.Response]:
    def inner(asset_slug: str) -> requests.Response:
        base_url = os.environ["FTT_API_URL"].rstrip("/")
        owner_token = token
        path = f"/v2/registry/academy/asset/{asset_slug}"
        url = f"{base_url}{path}"
        headers = build_headers(authorization=f"Token {owner_token}", accept="application/json", academy=academy)
        res = requests.get(url, headers=headers)
        return res

    return inner
