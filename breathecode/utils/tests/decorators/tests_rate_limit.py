import asyncio
from unittest.mock import MagicMock

import pytest
from django.core.cache import cache
from django.http import HttpResponse
from django.test import RequestFactory
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory

from breathecode.utils.decorators.rate_limit import RateLimiter, parse_rate, rate_limit


@pytest.fixture(autouse=True)
def setup(db, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("RATE_LIMIT_ENABLED", raising=False)
    monkeypatch.delenv("RATE_LIMIT_DISABLED_SCOPES", raising=False)
    yield


@pytest.mark.parametrize(
    "rate, expected",
    [("10/h", (10, 3600)), ("5/15m", (5, 900)), ("1/s", (1, 1)), ("3/2d", (3, 172800)), ("7/900s", (7, 900))],
)
def test_parse_rate(rate, expected):
    assert parse_rate(rate) == expected


@pytest.mark.parametrize("rate", ["10", "10/hour", "/h", "a/h", "10/0.5h"])
def test_parse_rate__invalid(rate):
    with pytest.raises(ValueError):
        parse_rate(rate)


class TestRateLimiter:

    def test_counts_hits_until_the_limit(self):
        limiter = RateLimiter("scope", "2/m")

        assert limiter.hit("ip", "1.1.1.1") == (True, 0)
        assert limiter.hit("ip", "1.1.1.1") == (True, 0)
        assert limiter.hit("ip", "1.1.1.1") == (False, 60)
        assert limiter.hit("ip", "2.2.2.2") == (True, 0)

    def test_count_and_is_limited_do_not_add_hits(self):
        limiter = RateLimiter("scope", "2/m")

        assert limiter.count("ip", "1.1.1.1") == 0
        assert limiter.is_limited("ip", "1.1.1.1") is False

        limiter.hit("ip", "1.1.1.1")
        limiter.hit("ip", "1.1.1.1")

        assert limiter.count("ip", "1.1.1.1") == 2
        assert limiter.is_limited("ip", "1.1.1.1") is True

    def test_reset(self):
        limiter = RateLimiter("scope", "1/m")
        limiter.hit("ip", "1.1.1.1")

        limiter.reset("ip", "1.1.1.1")

        assert limiter.hit("ip", "1.1.1.1") == (True, 0)

    def test_scopes_are_isolated(self):
        RateLimiter("a", "1/m").hit("ip", "1.1.1.1")

        assert RateLimiter("b", "1/m").hit("ip", "1.1.1.1") == (True, 0)

    def test_values_are_hashed(self):
        RateLimiter("scope", "1/m").hit("email", "konan@naruto.io")

        keys = cache.keys("ratelimit:*")
        assert len(keys) == 1
        assert keys[0].startswith("ratelimit:scope:email:")
        assert "konan" not in keys[0]

    def test_retry_after_uses_the_key_ttl(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(cache, "ttl", lambda key: 42, raising=False)
        limiter = RateLimiter("scope", "1/m")
        limiter.hit("ip", "1.1.1.1")

        assert limiter.hit("ip", "1.1.1.1") == (False, 42)

    def test_fails_open_when_the_cache_errors(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(cache, "add", MagicMock(side_effect=ConnectionError("redis down")))
        limiter = RateLimiter("scope", "1/m")

        assert limiter.hit("ip", "1.1.1.1") == (True, 0)
        assert limiter.hit("ip", "1.1.1.1") == (True, 0)

    def test_fails_open_when_cache_errors_are_ignored(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(cache, "add", MagicMock(return_value=None))
        monkeypatch.setattr(cache, "incr", MagicMock(return_value=None))
        limiter = RateLimiter("scope", "1/m")

        assert limiter.hit("ip", "1.1.1.1") == (True, 0)
        assert limiter.hit("ip", "1.1.1.1") == (True, 0)


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
@rate_limit("drf", "2/m", key="body:email", methods=("POST",))
def drf_view(request):
    return Response({"rate_limited": getattr(request, "rate_limited", False)})


@api_view(["POST"])
@permission_classes([AllowAny])
@rate_limit("drf-silent", "1/m", key="body:email", silent=True)
def drf_silent_view(request):
    return Response({"rate_limited": getattr(request, "rate_limited", False)})


@rate_limit("django", "1/m", key="ip")
def django_view(request):
    return HttpResponse("ok")


@rate_limit("django-async", "1/m", key="ip")
async def django_async_view(request):
    return HttpResponse("ok")


def post_email(view, email):
    request = APIRequestFactory().post("/", {"email": email}, format="json")
    return view(request)


class TestDecorator:

    def test_drf_view__rejects_with_429(self):
        assert post_email(drf_view, "konan@naruto.io").status_code == 200
        assert post_email(drf_view, "KONAN@naruto.io ").status_code == 200

        response = post_email(drf_view, "konan@naruto.io")

        assert response.status_code == 429
        assert response["Retry-After"] == "60"
        assert response.data == {"detail": "rate-limit-exceeded", "status_code": 429}

    def test_drf_view__without_key_value_is_not_limited(self):
        for _ in range(3):
            response = drf_view(APIRequestFactory().post("/", {}, format="json"))
            assert response.status_code == 200

    def test_drf_view__methods_not_listed_are_not_limited(self):
        for _ in range(3):
            assert drf_view(APIRequestFactory().get("/")).status_code == 200

        assert cache.keys("ratelimit:*") == []

    def test_silent__marks_the_request_and_calls_the_view(self):
        assert post_email(drf_silent_view, "konan@naruto.io").data == {"rate_limited": False}

        response = post_email(drf_silent_view, "konan@naruto.io")

        assert response.status_code == 200
        assert response.data == {"rate_limited": True}

    def test_django_view__renders_429(self):
        request = RequestFactory().post("/", REMOTE_ADDR="1.1.1.1")
        assert django_view(request).status_code == 200

        response = django_view(RequestFactory().post("/", REMOTE_ADDR="1.1.1.1"))

        assert response.status_code == 429
        assert response["Retry-After"] == "60"
        assert b"Too many requests" in response.content

    def test_async_view(self):
        assert asyncio.run(django_async_view(RequestFactory().get("/", REMOTE_ADDR="1.1.1.1"))).status_code == 200

        response = asyncio.run(django_async_view(RequestFactory().get("/", REMOTE_ADDR="1.1.1.1")))

        assert response.status_code == 429

    @pytest.mark.parametrize(
        "env",
        [{"RATE_LIMIT_ENABLED": "false"}, {"RATE_LIMIT_DISABLED_SCOPES": "other, drf"}],
    )
    def test_disabled_by_flag(self, monkeypatch: pytest.MonkeyPatch, env):
        for name, value in env.items():
            monkeypatch.setenv(name, value)

        for _ in range(3):
            assert post_email(drf_view, "konan@naruto.io").status_code == 200
