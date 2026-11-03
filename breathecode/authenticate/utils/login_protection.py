"""Login protection helpers: Turnstile CAPTCHA and failed-attempt rate limiting."""

from __future__ import annotations

import logging
import os
from typing import Optional

from breathecode.services.cloudflare import Turnstile
from breathecode.utils.decorators.rate_limit import RateLimiter
from breathecode.utils.request import get_client_ip

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


def _login_failure_limiter() -> RateLimiter:
    return RateLimiter("login-failure", f"{_rate_limit_max_attempts()}/{_rate_limit_window_seconds()}s")


def is_login_rate_limited(request, email: Optional[str] = None) -> bool:
    if not is_login_rate_limit_enabled():
        return False

    limiter = _login_failure_limiter()
    if limiter.is_limited("ip", get_client_ip(request)):
        return True

    normalized = _normalize_email(email)
    if normalized and limiter.is_limited("email", normalized):
        return True

    return False


def check_login_rate_limit(request, email: Optional[str] = None) -> None:
    """Raise LoginRateLimitExceeded when the IP or email is over the threshold."""
    if is_login_rate_limited(request, email):
        raise LoginRateLimitExceeded()


def record_login_failure(request, email: Optional[str] = None) -> None:
    if not is_login_rate_limit_enabled():
        return

    limiter = _login_failure_limiter()
    limiter.hit("ip", get_client_ip(request))

    normalized = _normalize_email(email)
    if normalized:
        limiter.hit("email", normalized)


def clear_login_rate_limit(request, email: Optional[str] = None) -> None:
    if not is_login_rate_limit_enabled():
        return

    limiter = _login_failure_limiter()
    limiter.reset("ip", get_client_ip(request))
    normalized = _normalize_email(email)
    if normalized:
        limiter.reset("email", normalized)
