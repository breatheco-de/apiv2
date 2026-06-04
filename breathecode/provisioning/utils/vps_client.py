"""
Vendor-agnostic VPS provisioning interface and registry.

Implementations (e.g. Hostinger) are registered by vendor slug; tasks/actions/views
resolve the client from the registry and call create_vps / destroy_vps / test_connection.
"""

from typing import Any, Dict, Optional, Protocol, runtime_checkable


class VPSProvisioningError(Exception):
    """Raised when VPS provisioning/deprovisioning or connection checks fail."""

    pass


@runtime_checkable
class VPSProvisioningClient(Protocol):
    """Protocol for VPS vendor implementations."""

    def create_vps(
        self,
        credentials: Dict[str, Any],
        plan_slug: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        ...

    def destroy_vps(self, credentials: Dict[str, Any], external_id: str) -> None:
        ...

    def test_connection(self, credentials: Dict[str, Any]) -> None:
        """Validate credentials/network connectivity for this VPS vendor."""
        ...


_vps_client_registry: Dict[str, type] = {}


def register_vps_client(vendor_slug: str):
    def decorator(cls: type):
        _vps_client_registry[vendor_slug.lower().strip()] = cls
        return cls

    return decorator


def get_vps_client(vendor) -> Optional[VPSProvisioningClient]:
    if vendor is None:
        return None
    slug = getattr(vendor, "name", vendor)
    if hasattr(slug, "lower"):
        slug = slug.lower().strip()
    else:
        slug = str(slug).lower().strip()
    client_class = _vps_client_registry.get(slug)
    if client_class is None:
        return None
    return client_class()
