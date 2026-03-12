"""
Vendor-agnostic VPS provisioning interface and registry.

Implementations (e.g. Hostinger) are registered by vendor slug; tasks and actions
resolve the client from the registry and call create_vps / destroy_vps only.
"""

from typing import Any, Dict, Optional, Protocol, runtime_checkable


class VPSProvisioningError(Exception):
    """Raised when VPS provisioning or deprovisioning fails (vendor API errors)."""

    pass


@runtime_checkable
class VPSProvisioningClient(Protocol):
    """Protocol for VPS vendor implementations. All return values are normalized."""

    def create_vps(
        self,
        credentials: Dict[str, Any],
        plan_slug: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Create a VPS. Returns normalized result with keys:
        external_id, ip_address, hostname, ssh_user, ssh_port, root_password (or None).
        Raises VPSProvisioningError on API errors.
        """
        ...

    def destroy_vps(self, credentials: Dict[str, Any], external_id: str) -> None:
        """
        Deprovision the VPS identified by external_id.
        Raises VPSProvisioningError on API errors.
        """
        ...


# Registry: vendor slug (lowercase) -> client class (instantiated with no args, or callable returning client)
_vps_client_registry: Dict[str, type] = {}


def register_vps_client(vendor_slug: str):
    """Decorator to register a VPS client class for a vendor slug."""

    def decorator(cls: type):
        _vps_client_registry[vendor_slug.lower().strip()] = cls
        return cls

    return decorator


def get_vps_client(vendor) -> Optional[VPSProvisioningClient]:
    """
    Resolve VPS client for the given ProvisioningVendor (model or name/slug string).
    Returns None if vendor is not registered.
    """
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
