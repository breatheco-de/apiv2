"""LLM vendor registry and client resolution for provisioning."""

from __future__ import annotations

from typing import Any, Dict, Optional, Protocol, Type

__all__ = [
    "LLMClient",
    "LLMClientError",
    "LLMConnectionError",
    "register_llm_client",
    "get_llm_client",
]

_llm_client_registry: Dict[str, Any] = {}


class LLMClientError(Exception):
    """Base exception for LLM client errors (vendor/provider API errors)."""


class LLMConnectionError(Exception):
    """Raised when an LLM vendor connection check fails."""

    pass


class LLMClient(Protocol):
    """
    Minimal interface expected by our provisioning workflows.

    Concrete clients should generally raise `LLMClientError` (or subclasses)
    so callers can retry consistently.
    """

    def test_connection(self, timeout: float = 15.0) -> None:  # pragma: no cover
        ...

    def create_api_key(
        self,
        external_user_id: str,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timeout: float = 10.0,
    ) -> Dict[str, Any]: ...

    def delete_api_keys(
        self,
        user_id: str,
        token_ids: Optional[list[str]] = None,
        timeout: float = 10.0,
    ) -> bool: ...

    def get_user_info(self, user_id: str, timeout: float = 10.0) -> Dict[str, Any]: ...

    def create_user(
        self,
        user_id: str,
        user_alias: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timeout: float = 10.0,
    ) -> Dict[str, Any]: ...

    def delete_user(self, user_ids: list[str], timeout: float = 10.0) -> bool: ...


def register_llm_client(vendor_slug: str):
    """Decorator to register an LLM client class for a vendor slug."""

    def decorator(cls: Type):
        _llm_client_registry[vendor_slug.lower().strip()] = cls
        return cls

    return decorator


def get_llm_client(provisioning_academy: Any) -> Optional[LLMClient]:
    """
    Resolve an LLM client *instance* from a `ProvisioningAcademy` configuration.

    Returns an instantiated client or None.
    """
    if provisioning_academy is None:
        return None

    vendor = getattr(provisioning_academy, "vendor", None)
    if vendor is None:
        return None

    slug = getattr(vendor, "name", vendor)
    slug = str(slug).lower().strip()
    client_class = _llm_client_registry.get(slug)
    if client_class is None:
        return None

    api_url = getattr(vendor, "api_url", None)
    if not api_url:
        return None

    api_key = getattr(provisioning_academy, "credentials_token", None) or getattr(
        provisioning_academy, "credentials_key", None
    )
    if not api_key:
        return None

    base_url = api_url.rstrip("/") if isinstance(api_url, str) else api_url
    return client_class(base_url=base_url, api_key=api_key)
