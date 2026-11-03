"""Fixed-window rate limiting backed by the Django cache (Redis)."""

import functools
import hashlib
import inspect
import logging
import re
from typing import Any, Callable, Optional

from capyc.core.i18n import translation
from capyc.core.managers import feature
from capyc.rest_framework.exceptions import ValidationException
from django import shortcuts
from django.core.cache import cache
from django.views import View
from rest_framework.request import Request

from breathecode.utils.request import get_client_ip

logger = logging.getLogger(__name__)

__all__ = ["RateLimiter", "RateLimitExceeded", "rate_limit", "parse_rate"]

RATE_UNITS = {"s": 1, "m": 60, "h": 60 * 60, "d": 60 * 60 * 24}
RATE_PATTERN = re.compile(r"^(\d+)/(\d*)([smhd])$")

KeyFunction = Callable[..., Optional[str]]


def parse_rate(rate: str) -> tuple[int, int]:
    """Parse rates like `10/h` or `5/15m` into `(limit, window_seconds)`."""
    match = RATE_PATTERN.match(rate.strip())
    if match is None:
        raise ValueError(f"Invalid rate {rate!r}, expected a value like '10/h' or '5/15m'")

    limit, multiplier, unit = match.groups()
    return int(limit), int(multiplier or 1) * RATE_UNITS[unit]


class RateLimitExceeded(ValidationException):
    def __init__(self, retry_after: int, lang: str = "en"):
        # read by the DRF exception handler to set the Retry-After header
        self.wait = retry_after
        super().__init__(
            translation(
                lang,
                en="Too many requests, please try again later",
                es="Demasiadas solicitudes, por favor intenta más tarde",
                slug="rate-limit-exceeded",
            ),
            code=429,
            slug="rate-limit-exceeded",
        )


class RateLimiter:
    """
    Count hits per `(scope, key_name, value)` in a fixed window.

    Values are hashed so the cache never stores raw emails or IPs. Cache errors fail open.
    """

    def __init__(self, scope: str, rate: str):
        self.scope = scope
        self.limit, self.window = parse_rate(rate)

    def _key(self, key_name: str, value: Any) -> str:
        digest = hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:16]
        return f"ratelimit:{self.scope}:{key_name}:{digest}"

    def _incr(self, key: str) -> Optional[int]:
        cache.add(key, 0, timeout=self.window)
        try:
            return cache.incr(key)
        except ValueError:
            # the key expired between add and incr
            cache.add(key, 0, timeout=self.window)
            return cache.incr(key)

    def _retry_after(self, key: str) -> int:
        get_ttl = getattr(cache, "ttl", None)
        if get_ttl is not None:
            try:
                seconds = get_ttl(key)
            except Exception:
                seconds = None

            if isinstance(seconds, int) and seconds > 0:
                return seconds

        return self.window

    def hit(self, key_name: str, value: Any) -> tuple[bool, int]:
        """Record a hit, return `(allowed, retry_after_seconds)`."""
        key = self._key(key_name, value)
        try:
            count = self._incr(key)
        except Exception:
            logger.exception("Rate limiter unavailable for scope %s", self.scope)
            return True, 0

        if count is None or count <= self.limit:
            return True, 0

        return False, self._retry_after(key)

    def count(self, key_name: str, value: Any) -> int:
        """Return the hits recorded in the current window without adding one."""
        try:
            return cache.incr(self._key(key_name, value), 0) or 0
        except ValueError:
            return 0
        except Exception:
            logger.exception("Rate limiter unavailable for scope %s", self.scope)
            return 0

    def is_limited(self, key_name: str, value: Any) -> bool:
        return self.count(key_name, value) >= self.limit

    def reset(self, key_name: str, value: Any) -> None:
        try:
            cache.delete(self._key(key_name, value))
        except Exception:
            logger.exception("Rate limiter unavailable for scope %s", self.scope)


def _get_request(args: tuple) -> Any:
    if args and isinstance(args[0], View):
        return args[1]

    return args[0]


def _get_payload_value(request, name: str) -> Any:
    if isinstance(request, Request):
        data = request.data
    else:
        data = request.POST

    return data.get(name) if hasattr(data, "get") else None


def _resolve_key(key: str | KeyFunction, request, args: tuple, kwargs: dict) -> tuple[str, Optional[str]]:
    if callable(key):
        return getattr(key, "__name__", "custom"), key(request, *args, **kwargs)

    if key == "ip":
        return key, get_client_ip(request)

    if key == "user":
        user = getattr(request, "user", None)
        return key, str(user.id) if user is not None and user.is_authenticated else None

    source, _, name = key.partition(":")
    if source == "body":
        value = _get_payload_value(request, name)
    elif source == "query":
        value = request.GET.get(name)
    elif source == "kwarg":
        value = kwargs.get(name)
    else:
        raise ValueError(f"Invalid rate limit key {key!r}")

    if name == "email" and isinstance(value, str):
        value = value.strip().lower()

    return key, str(value) if value not in (None, "") else None


def is_rate_limit_enabled(scope: str) -> bool:
    return feature.is_enabled("authenticate.rate_limit", context=feature.context(scope=scope), default=True)


def _rate_limited_response(request, retry_after: int):
    lang = request.META.get("HTTP_ACCEPT_LANGUAGE") or "en"
    if isinstance(request, Request):
        raise RateLimitExceeded(retry_after, lang)

    response = shortcuts.render(
        request,
        "message.html",
        {
            "MESSAGE": translation(
                lang,
                en="Too many requests, please try again later",
                es="Demasiadas solicitudes, por favor intenta más tarde",
            )
        },
        status=429,
    )
    response["Retry-After"] = str(retry_after)
    return response


def rate_limit(
    scope: str,
    rate: str,
    key: str | KeyFunction = "ip",
    silent: bool = False,
    methods: Optional[tuple[str, ...]] = None,
):
    """
    Limit how often a view can be called.

    Arguments:
        scope: name shared by every limit of the same action, it can be disabled with the `authenticate.rate_limit`
            flag (`RATE_LIMIT_ENABLED`, `RATE_LIMIT_DISABLED_SCOPES`).
        rate: `<hits>/<window>`, e.g. `10/h`, `5/15m`.
        key: `ip`, `user`, `body:<field>`, `query:<field>`, `kwarg:<url kwarg>` or a callable receiving
            `(request, *args, **kwargs)`. Requests without a value for the key are not limited.
        silent: instead of rejecting, set `request.rate_limited = True` and call the view, so it can skip the
            action while returning its usual response (useful to avoid account enumeration).
        methods: HTTP methods to limit, all of them by default.

    Rejected requests get a 429 with `Retry-After`: a `RateLimitExceeded` for DRF views or a rendered message for
    plain Django views. Stack the decorator to apply several limits.
    """
    limiter = RateLimiter(scope, rate)

    def check(args: tuple, kwargs: dict) -> tuple[Any, Optional[int]]:
        request = _get_request(args)
        if methods is not None and request.method not in methods:
            return request, None

        if not is_rate_limit_enabled(scope):
            return request, None

        key_name, value = _resolve_key(key, request, args, kwargs)
        if value is None:
            return request, None

        allowed, retry_after = limiter.hit(key_name, value)
        if allowed:
            return request, None

        logger.warning("Rate limit exceeded for scope %s by %s", scope, key_name)
        if silent:
            request.rate_limited = True
            return request, None

        return request, retry_after

    def decorator(function):
        if inspect.iscoroutinefunction(function):

            @functools.wraps(function)
            async def async_wrapper(*args, **kwargs):
                request, retry_after = check(args, kwargs)
                if retry_after is not None:
                    return _rate_limited_response(request, retry_after)

                return await function(*args, **kwargs)

            return async_wrapper

        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            request, retry_after = check(args, kwargs)
            if retry_after is not None:
                return _rate_limited_response(request, retry_after)

            return function(*args, **kwargs)

        return wrapper

    return decorator
