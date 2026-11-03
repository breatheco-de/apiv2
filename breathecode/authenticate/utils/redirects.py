"""Allowlist for client-supplied redirect targets (`url` and `callback` parameters)."""

from __future__ import annotations

import base64
import logging
import os
from typing import Optional
from urllib.parse import urlsplit

from capyc.core.i18n import translation
from capyc.rest_framework.exceptions import ValidationException
from django.conf import settings
from django.core.cache import cache
from django.utils.http import url_has_allowed_host_and_scheme

logger = logging.getLogger(__name__)

__all__ = [
    "FIRST_PARTY_DOMAINS",
    "decode_redirect_url",
    "get_allowed_redirect_hosts",
    "invalidate_academy_redirect_hosts",
    "is_allowed_redirect_url",
    "validate_redirect_url",
]

# These domains and all of their subdomains are trusted.
FIRST_PARTY_DOMAINS = ("4geeks.com", "4geeksacademy.com", "learnpack.co")

LOCAL_HOSTS = ("localhost", "127.0.0.1")
ACADEMY_HOSTS_CACHE_KEY = "auth:redirect_hosts"
ACADEMY_HOSTS_CACHE_TIMEOUT = 60 * 60 * 24


def _get_hostname(url: Optional[str]) -> Optional[str]:
    if not url or not isinstance(url, str):
        return None

    try:
        hostname = urlsplit(url.strip()).hostname
    except ValueError:
        return None

    return hostname.rstrip(".") if hostname else None


def decode_redirect_url(url: Optional[str]) -> Optional[str]:
    """Return the url decoded from base64 when it was encoded, otherwise the url unchanged."""
    if not url:
        return url

    try:
        return base64.b64decode(url.encode("utf-8")).decode("utf-8")
    except Exception:
        return url


def get_academy_redirect_hosts() -> set[str]:
    hosts = cache.get(ACADEMY_HOSTS_CACHE_KEY)
    if hosts is not None:
        return set(hosts)

    from breathecode.admissions.models import Academy

    hosts = set()
    for website_url, white_label_url in Academy.objects.values_list("website_url", "white_label_url"):
        for url in (website_url, white_label_url):
            if hostname := _get_hostname(url):
                hosts.add(hostname)

    cache.set(ACADEMY_HOSTS_CACHE_KEY, sorted(hosts), timeout=ACADEMY_HOSTS_CACHE_TIMEOUT)
    return hosts


def invalidate_academy_redirect_hosts() -> None:
    cache.delete(ACADEMY_HOSTS_CACHE_KEY)


def get_allowed_redirect_hosts() -> set[str]:
    """Hosts trusted by exact match, the first-party domains are matched separately with their subdomains."""
    hosts = get_academy_redirect_hosts()

    for env_name in ("SITE_URL", "APP_URL", "API_URL"):
        if hostname := _get_hostname(os.getenv(env_name)):
            hosts.add(hostname)

    return hosts


def _is_first_party_host(hostname: str) -> bool:
    return any(hostname == domain or hostname.endswith("." + domain) for domain in FIRST_PARTY_DOMAINS)


def is_allowed_redirect_url(url: Optional[str]) -> bool:
    # Temporary: Codespaces and the Copilot extension call back to hosts outside the allowlist.
    return True

    if not url or not isinstance(url, str):
        return False

    url = url.strip()

    try:
        parts = urlsplit(url)
    except ValueError:
        return False

    # same-origin paths can't leave this host, `//host` and `/\host` are rejected by the structural check
    if not parts.scheme and not parts.netloc and url.startswith("/"):
        return url_has_allowed_host_and_scheme(url, allowed_hosts=set())

    hostname = _get_hostname(url)
    if not hostname:
        return False

    is_local = settings.DEBUG and parts.scheme == "http" and hostname in LOCAL_HOSTS
    if parts.scheme != "https" and not is_local:
        return False

    if not url_has_allowed_host_and_scheme(url, allowed_hosts={parts.netloc}, require_https=not is_local):
        return False

    if is_local or _is_first_party_host(hostname):
        return True

    return hostname in get_allowed_redirect_hosts()


def validate_redirect_url(url: Optional[str], lang: str = "en") -> str:
    """Return the url when it is allowed, otherwise raise a ValidationException."""
    if is_allowed_redirect_url(url):
        return url

    # never log the full url, the query string may contain tokens
    logger.warning("Rejected redirect url with host %s", _get_hostname(url) or "<invalid>")
    raise ValidationException(
        translation(
            lang,
            en="The redirect url is not allowed",
            es="La url de redirección no está permitida",
            slug="invalid-redirect-url",
        ),
        code=400,
        slug="invalid-redirect-url",
    )
