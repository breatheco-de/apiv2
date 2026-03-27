"""Coding editor vendor connection interface and registry (Codespaces, Gitpod, ...)."""

from typing import Any, Dict, Optional, Protocol, runtime_checkable

from breathecode.services.github import Github, GithubAuthException


class CodingEditorConnectionError(Exception):
    """Raised when a coding editor vendor connection check fails."""

    pass


@runtime_checkable
class CodingEditorClient(Protocol):
    def test_connection(self, credentials: Dict[str, Any], vendor: Any = None) -> None:
        ...


_coding_editor_client_registry: Dict[str, type] = {}


def register_coding_editor_client(vendor_slug: str):
    def decorator(cls: type):
        _coding_editor_client_registry[vendor_slug.lower().strip()] = cls
        return cls

    return decorator


def get_coding_editor_client(vendor) -> Optional[CodingEditorClient]:
    if vendor is None:
        return None
    slug = getattr(vendor, "name", vendor)
    if hasattr(slug, "lower"):
        slug = slug.lower().strip()
    else:
        slug = str(slug).lower().strip()
    client_class = _coding_editor_client_registry.get(slug)
    if client_class is None:
        return None
    return client_class()


@register_coding_editor_client("codespaces")
class CodespacesCodingEditorClient:
    def test_connection(self, credentials: Dict[str, Any], vendor: Any = None) -> None:
        token = credentials.get("token") or credentials.get("access_token")
        if not token:
            raise CodingEditorConnectionError("Codespaces credentials missing token")

        host = getattr(vendor, "api_url", None) if vendor else None
        host = host or None
        github = Github(token=token, host=host)
        try:
            github.get("/user")
        except GithubAuthException as e:
            raise CodingEditorConnectionError(f"GitHub auth failed: {e}") from e
        except Exception as e:
            raise CodingEditorConnectionError(f"GitHub connection failed: {e}") from e
