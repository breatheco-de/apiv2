"""Login protection helpers: Turnstile CAPTCHA and failed-attempt rate limiting."""

from __future__ import annotations

import logging
import os
from typing import Optional

from django.core.cache import cache

from breathecode.services.cloudflare import Turnstile

logger = logging.getLogger(__name__)

__all__ = [
    "LoginRateLimitExceeded",
    "clear_login_rate_limit",
    "check_login_rate_limit",
    "get_client_ip",
    "get_login_captcha_context",
    "is_captcha_enabled",
    "is_login_rate_limit_enabled",
    "record_login_failure",
    "verify_turnstile_if_enabled",
]


class LoginRateLimitExceeded(Exception):
    """Raised when too many failed login attempts have been recorded."""

    def __init__(self, message: str = "Too many login attempts. Please try again later."):
        self.message = message
        super().__init__(message)


def is_captcha_enabled() -> bool:
    apply_captcha = os.getenv("APPLY_CAPTCHA", "FALSE").lower()
    return bool(apply_captcha) and apply_captcha != "false"


def is_login_rate_limit_enabled() -> bool:
    enabled = os.getenv("LOGIN_RATE_LIMIT_ENABLED", "FALSE").lower()
    return bool(enabled) and enabled != "false"


def get_client_ip(request) -> str:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR") or "unknown"


def get_login_captcha_context() -> dict:
    return {
        "apply_captcha": is_captcha_enabled(),
        "turnstile_site_key": os.getenv("CLOUDFLARE_TURNSTILE_SITE_KEY", ""),
    }


def verify_turnstile_if_enabled(request) -> None:
    """Verify Cloudflare Turnstile token when APPLY_CAPTCHA is enabled.

    Raises:
        ValidationException: If verification fails or token/secret is missing.
    """
    if not is_captcha_enabled():
        return

    token = request.POST.get("cf-turnstile-response")
    if not token and hasattr(request, "data"):
        data = request.data
        if hasattr(data, "get"):
            token = data.get("cf-turnstile-response")

    secret = os.getenv("CLOUDFLARE_TURNSTILE_SECRET_KEY", "")
    Turnstile().verify_token(secret_key=secret, token=token, remoteip=get_client_ip(request))


def _rate_limit_max_attempts() -> int:
    try:
        return max(1, int(os.getenv("LOGIN_RATE_LIMIT_MAX_ATTEMPTS", "5")))
    except ValueError:
        return 5


def _rate_limit_window_seconds() -> int:
    try:
        return max(1, int(os.getenv("LOGIN_RATE_LIMIT_WINDOW_SECONDS", "900")))
    except ValueError:
        return 900


def _normalize_email(email: Optional[str]) -> Optional[str]:
    if not email:
        return None
    return email.strip().lower()


def _ip_cache_key(ip: str) -> str:
    return f"login_fail:ip:{ip}"


def _email_cache_key(email: str) -> str:
    return f"login_fail:email:{email}"


def _get_failure_count(key: str) -> int:
    value = cache.get(key)
    if value is None:
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def is_login_rate_limited(request, email: Optional[str] = None) -> bool:
    if not is_login_rate_limit_enabled():
        return False

    max_attempts = _rate_limit_max_attempts()
    ip = get_client_ip(request)
    if _get_failure_count(_ip_cache_key(ip)) >= max_attempts:
        return True

    normalized = _normalize_email(email)
    if normalized and _get_failure_count(_email_cache_key(normalized)) >= max_attempts:
        return True

    return False


def check_login_rate_limit(request, email: Optional[str] = None) -> None:
    """Raise LoginRateLimitExceeded when the IP or email is over the threshold."""
    if is_login_rate_limited(request, email):
        raise LoginRateLimitExceeded()


def record_login_failure(request, email: Optional[str] = None) -> None:
    if not is_login_rate_limit_enabled():
        return

    window = _rate_limit_window_seconds()
    ip = get_client_ip(request)
    ip_key = _ip_cache_key(ip)
    cache.set(ip_key, _get_failure_count(ip_key) + 1, timeout=window)

    normalized = _normalize_email(email)
    if normalized:
        email_key = _email_cache_key(normalized)
        cache.set(email_key, _get_failure_count(email_key) + 1, timeout=window)


def clear_login_rate_limit(request, email: Optional[str] = None) -> None:
    if not is_login_rate_limit_enabled():
        return

    cache.delete(_ip_cache_key(get_client_ip(request)))
    normalized = _normalize_email(email)
    if normalized:
        cache.delete(_email_cache_key(normalized))
