from __future__ import annotations

from typing import Any, Dict, Optional, Protocol, Type

__all__ = [
    "LLMClientError",
    "register_llm_client",
    "get_llm_client_class",
    "get_llm_client",
]

_llm_client_registry: Dict[str, Any] = {}


class LLMClientError(Exception):
    """Base exception for LLM client errors (vendor/provider API errors)."""


class LLMClient(Protocol):
    """
    Minimal interface expected by our provisioning workflows.

    Concrete clients should generally raise `LLMClientError` (or subclasses)
    so callers can retry consistently.
    """

    def delete_user(self, user_ids: list[str], **kwargs: Any) -> bool:  # pragma: no cover
        ...


def register_llm_client(vendor_slug: str):
    """
    Decorator to register an LLM client class for a vendor slug.
    """

    def decorator(cls: Type):
        _llm_client_registry[vendor_slug.lower().strip()] = cls
        return cls

    return decorator


def get_llm_client_class(vendor: Any) -> Optional[Type]:
    """
    Resolve the registered LLM client class for a ProvisioningVendor (model) or string.
    Returns None if the vendor is not registered/supported.
    """
    if vendor is None:
        return None

    slug = getattr(vendor, "name", vendor)
    slug = str(slug).lower().strip()
    return _llm_client_registry.get(slug)


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

    client_class = get_llm_client_class(vendor)
    if client_class is None:
        return None

    api_url = getattr(vendor, "api_url", None)
    if not api_url:
        return None

    # Prefer credentials_token as the bearer token if present.
    api_key = getattr(provisioning_academy, "credentials_token", None) or getattr(
        provisioning_academy, "credentials_key", None
    )
    if not api_key:
        return None

    base_url = api_url.rstrip("/") if isinstance(api_url, str) else api_url
    return client_class(base_url=base_url, api_key=api_key)
