"""
Hostinger VPS client implementing the provisioning VPS client interface.

Uses Hostinger API SDK: purchase VPS, get details, cancel subscription for destroy.
Credentials dict: token (required), optionally item_id, template_id, data_center_id.
"""

import logging
import secrets
import string
from typing import Any, Dict, Optional

from breathecode.provisioning.vps_client import VPSProvisioningError, register_vps_client

logger = logging.getLogger(__name__)


def _generate_root_password(length: int = 24) -> str:
    """Generate a secure random password meeting typical VPS requirements."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


@register_vps_client("hostinger")
class HostingerVPSClient:
    """Hostinger implementation of VPS create_vps / destroy_vps."""

    def create_vps(
        self,
        credentials: Dict[str, Any],
        plan_slug: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Create a VPS via Hostinger API.
        credentials: token (required), optionally item_id, template_id, data_center_id.
        Returns normalized dict: external_id, ip_address, hostname, ssh_user, ssh_port, root_password.
        """
        try:
            import hostinger_api
            from hostinger_api.rest import ApiException
        except ImportError as e:
            raise VPSProvisioningError("Hostinger API SDK not installed") from e

        token = credentials.get("token") or credentials.get("access_token")
        if not token:
            raise VPSProvisioningError("Hostinger credentials missing token")

        configuration = hostinger_api.Configuration(access_token=token)
        root_password = _generate_root_password()

        with hostinger_api.ApiClient(configuration) as api_client:
            # Resolve item_id, template_id, data_center_id from credentials or API defaults
            item_id = credentials.get("item_id")
            template_id = credentials.get("template_id")
            data_center_id = credentials.get("data_center_id")
            defaults_lookup_error = None

            if not all([item_id, template_id, data_center_id]):
                try:
                    if not data_center_id:
                        dc_api = hostinger_api.VPSDataCentersApi(api_client)
                        dc_list = dc_api.get_data_center_list_v1()
                        if getattr(dc_list, "data", None) and len(dc_list.data) > 0:
                            data_center_id = getattr(dc_list.data[0], "id", None)
                    if not template_id:
                        templates_api = hostinger_api.VPSOSTemplatesApi(api_client)
                        templates = templates_api.get_templates_v1()
                        if getattr(templates, "data", None) and len(templates.data) > 0:
                            template_id = getattr(templates.data[0], "id", None)
                    if not item_id:
                        catalog_api = hostinger_api.BillingCatalogApi(api_client)
                        catalog = catalog_api.get_catalog_item_list_v1(category="VPS")
                        if getattr(catalog, "data", None) and len(catalog.data) > 0:
                            first = catalog.data[0]
                            item_id = str(getattr(first, "id", None) or getattr(first, "item_id", "") or "")
                except ApiException as e:
                    logger.warning("Hostinger defaults lookup failed: %s", e)
                    defaults_lookup_error = str(e)

            if not item_id or not template_id or not data_center_id:
                missing = [
                    key for key, value in (
                        ("item_id", item_id),
                        ("template_id", template_id),
                        ("data_center_id", data_center_id),
                    ) if not value
                ]
                details = f" Missing: {', '.join(missing)}."
                if defaults_lookup_error:
                    details += f" Hostinger defaults lookup failed: {defaults_lookup_error}"
                raise VPSProvisioningError(
                    "Missing item_id, template_id or data_center_id. "
                    "Set allowed options in ProvisioningAcademy vendor_settings and send selected values when requesting VPS."
                    + details
                )

            try:
                purchase_request = hostinger_api.VPSV1VirtualMachinePurchaseRequest(
                    item_id=str(item_id),
                    setup=hostinger_api.VPSV1VirtualMachineSetupRequest(
                        template_id=int(template_id),
                        data_center_id=int(data_center_id),
                        password=root_password,
                        install_monarx=False,
                        enable_backups=False,
                    ),
                )
                vps_api = hostinger_api.VPSVirtualMachineApi(api_client)
                order_response = vps_api.purchase_new_virtual_machine_v1(purchase_request)
            except ApiException as e:
                raise VPSProvisioningError(f"Hostinger create VPS failed: {e}") from e

            vm = getattr(order_response, "virtual_machine", None) or getattr(order_response, "virtual_machine_resource", None)
            if not vm:
                raise VPSProvisioningError("Hostinger purchase succeeded but no virtual_machine in response")

            external_id = str(getattr(vm, "id", None) or "")
            hostname = getattr(vm, "hostname", None) or ""
            ip_address = None
            ipv4 = getattr(vm, "ipv4", None) or []
            if ipv4 and len(ipv4) > 0:
                first_ip = ipv4[0]
                ip_address = getattr(first_ip, "address", None) or getattr(first_ip, "ip", None)

            return {
                "external_id": external_id,
                "ip_address": ip_address or "",
                "hostname": hostname or "",
                "ssh_user": "root",
                "ssh_port": 22,
                "root_password": root_password,
            }

    def destroy_vps(self, credentials: Dict[str, Any], external_id: str) -> None:
        """Deprovision the VPS by canceling its subscription."""
        try:
            import hostinger_api
            from hostinger_api.rest import ApiException
        except ImportError as e:
            raise VPSProvisioningError("Hostinger API SDK not installed") from e

        token = credentials.get("token") or credentials.get("access_token")
        if not token:
            raise VPSProvisioningError("Hostinger credentials missing token")

        configuration = hostinger_api.Configuration(access_token=token)
        with hostinger_api.ApiClient(configuration) as api_client:
            try:
                vps_api = hostinger_api.VPSVirtualMachineApi(api_client)
                vm_id = int(external_id)
                vm = vps_api.get_virtual_machine_details_v1(vm_id)
                subscription_id = getattr(vm, "subscription_id", None)
                if not subscription_id:
                    raise VPSProvisioningError("VPS has no subscription_id; cannot cancel")
                subs_api = hostinger_api.BillingSubscriptionsApi(api_client)
                subs_api.cancel_subscription_v1(subscription_id)
            except ApiException as e:
                raise VPSProvisioningError(f"Hostinger destroy VPS failed: {e}") from e
