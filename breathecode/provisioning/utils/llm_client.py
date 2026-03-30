"""LLM vendor connection interface and registry (LiteLLM and compatible providers)."""

from typing import Any, Dict, Optional, Protocol, runtime_checkable

import requests


class LLMConnectionError(Exception):
    """Raised when an LLM vendor connection check fails."""

    pass


@runtime_checkable
class LLMClient(Protocol):
    def test_connection(self, credentials: Dict[str, Any], vendor: Any = None) -> None:
        ...


_llm_client_registry: Dict[str, type] = {}


def register_llm_client(vendor_slug: str):
    def decorator(cls: type):
        _llm_client_registry[vendor_slug.lower().strip()] = cls
        return cls

    return decorator


def get_llm_client(vendor) -> Optional[LLMClient]:
    if vendor is None:
        return None
    slug = getattr(vendor, "name", vendor)
    if hasattr(slug, "lower"):
        slug = slug.lower().strip()
    else:
        slug = str(slug).lower().strip()
    client_class = _llm_client_registry.get(slug)
    if client_class is None:
        return None
    return client_class()


@register_llm_client("litellm")
class LiteLLMClient:
    """LiteLLM connection check using a lightweight models endpoint request."""

    def test_connection(self, credentials: Dict[str, Any], vendor: Any = None) -> None:
        token = credentials.get("token") or credentials.get("access_token")
        if not token:
            raise LLMConnectionError("LLM credentials missing token")

        base_url = (getattr(vendor, "api_url", None) or "").rstrip("/")
        if not base_url:
            raise LLMConnectionError("LLM vendor api_url is missing")

        try:
            response = requests.get(
                f"{base_url}/models",
                headers={"Authorization": f"Bearer {token}"},
                timeout=15,
            )
        except Exception as e:
            raise LLMConnectionError(f"LLM connection failed: {e}") from e

        if response.status_code >= 400:
            raise LLMConnectionError(f"LLM connection failed with status {response.status_code}")
