"""
DigitalOcean Droplets VPS client implementing the provisioning VPS client interface.

Uses DigitalOcean HTTP API v2: create droplet, poll until active, delete droplet.
Credentials dict: token (required), region_slug, size_slug, image_slug (from vendor_selection).
Optional provisioning_vps_id for stable droplet naming.
"""

import logging
import secrets
import string
import time
from typing import Any, Dict, List, Optional

import requests

from breathecode.provisioning.utils.vps_client import VPSProvisioningError, register_vps_client

logger = logging.getLogger(__name__)

DO_API_BASE = "https://api.digitalocean.com/v2"
POLL_INTERVAL_SEC = 5
POLL_MAX_ATTEMPTS = 60


def _generate_root_password(length: int = 32) -> str:
    """Alphanumeric only so cloud-init chpasswd list lines are YAML-safe (no # ' : etc.)."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _cloud_config_user_data(root_password: str) -> str:
    """Cloud-init to enable root SSH password login (Ubuntu/Debian-style images)."""
    return f"""#cloud-config
chpasswd:
  list: |
    root:{root_password}
  expire: false
ssh_pwauth: true
"""


def _do_request(
    method: str,
    token: str,
    path: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    json_body: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    url = f"{DO_API_BASE}{path}" if path.startswith("/") else f"{DO_API_BASE}/{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    try:
        resp = requests.request(method, url, headers=headers, params=params, json=json_body, timeout=60)
    except requests.RequestException as e:
        raise VPSProvisioningError(f"DigitalOcean request failed: {e}") from e
    try:
        data = resp.json() if resp.content else {}
    except ValueError:
        data = {}
    if resp.status_code >= 400:
        msg = data.get("message") or data.get("id") or resp.text or f"HTTP {resp.status_code}"
        raise VPSProvisioningError(f"DigitalOcean API error ({resp.status_code}): {msg}")
    return data if isinstance(data, dict) else {}


def _collect_paginated(token: str, path: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Follow DigitalOcean pagination links until no next page or max pages."""
    out: List[Dict[str, Any]] = []
    params = dict(params or {})
    params.setdefault("per_page", 100)
    page_url: Optional[str] = None
    max_pages = 50
    for _ in range(max_pages):
        if page_url:
            # next link is full URL
            try:
                r = requests.get(
                    page_url,
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                    timeout=60,
                )
            except requests.RequestException as e:
                raise VPSProvisioningError(f"DigitalOcean request failed: {e}") from e
            if r.status_code >= 400:
                try:
                    err = r.json()
                    msg = err.get("message") or r.text
                except ValueError:
                    msg = r.text
                raise VPSProvisioningError(f"DigitalOcean API error ({r.status_code}): {msg}")
            data = r.json() if r.content else {}
        else:
            data = _do_request("GET", token, path, params=params)

        # Response may be { regions: [...] } or { sizes: [...] } or { images: [...] }
        for key in ("regions", "sizes", "images", "droplets"):
            if key in data and isinstance(data[key], list):
                out.extend(data[key])
                break

        links = data.get("links") or {}
        pages = links.get("pages") or {}
        page_url = pages.get("next")
        if not page_url:
            break
    return out


@register_vps_client("digitalocean")
class DigitalOceanVPSClient:
    """DigitalOcean Droplets implementation of VPS create_vps / destroy_vps."""

    def create_vps(
        self,
        credentials: Dict[str, Any],
        plan_slug: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        token = credentials.get("token") or credentials.get("access_token")
        if not token:
            raise VPSProvisioningError("DigitalOcean credentials missing token")

        region = (credentials.get("region_slug") or "").strip()
        size = (credentials.get("size_slug") or "").strip()
        image = (credentials.get("image_slug") or "").strip()
        if not region or not size or not image:
            raise VPSProvisioningError(
                "Missing region_slug, size_slug or image_slug. "
                "Configure vendor_settings allowlists and send vendor_selection when requesting VPS."
            )

        vps_id = credentials.get("provisioning_vps_id")
        if vps_id is not None:
            name = f"bc-vps-{vps_id}"
        else:
            name = f"bc-vps-{secrets.token_hex(4)}"

        root_password = _generate_root_password()
        user_data = _cloud_config_user_data(root_password)

        body = {
            "name": name,
            "region": region,
            "size": size,
            "image": image,
            "user_data": user_data,
        }

        created = _do_request("POST", token, "/droplets", json_body=body)
        droplet = created.get("droplet") or {}
        droplet_id = droplet.get("id")
        if not droplet_id:
            raise VPSProvisioningError("DigitalOcean create droplet returned no droplet id")

        external_id = str(droplet_id)
        hostname = droplet.get("name") or name

        ip_address = ""
        for _ in range(POLL_MAX_ATTEMPTS):
            detail = _do_request("GET", token, f"/droplets/{external_id}")
            d = detail.get("droplet") or {}
            status = (d.get("status") or "").lower()
            networks = d.get("networks") or {}
            for v4 in networks.get("v4") or []:
                if v4.get("type") == "public":
                    ip_address = v4.get("ip_address") or ""
                    break
            if status == "active" and ip_address:
                break
            if status in ("error", "archive"):
                raise VPSProvisioningError(f"Droplet entered bad status: {status}")
            time.sleep(POLL_INTERVAL_SEC)
        else:
            raise VPSProvisioningError("DigitalOcean droplet did not become active with a public IP in time")

        return {
            "external_id": external_id,
            "ip_address": ip_address,
            "hostname": hostname,
            "ssh_user": "root",
            "ssh_port": 22,
            "root_password": root_password,
        }

    def destroy_vps(self, credentials: Dict[str, Any], external_id: str) -> None:
        token = credentials.get("token") or credentials.get("access_token")
        if not token:
            raise VPSProvisioningError("DigitalOcean credentials missing token")
        try:
            droplet_id = int(str(external_id).strip())
        except ValueError as e:
            raise VPSProvisioningError(f"Invalid DigitalOcean droplet id: {external_id}") from e
        _do_request("DELETE", token, f"/droplets/{droplet_id}")

    def test_connection(self, credentials: Dict[str, Any]) -> None:
        token = credentials.get("token") or credentials.get("access_token")
        if not token:
            raise VPSProvisioningError("DigitalOcean credentials missing token")
        _do_request("GET", token, "/account")


def fetch_vendor_options(token: str) -> Dict[str, Any]:
    """
    List regions, sizes, and distribution images for vendor-options endpoint.
    Raises VPSProvisioningError on API failure.
    """
    if not token:
        raise VPSProvisioningError("DigitalOcean credentials missing token")

    regions_raw = _collect_paginated(token, "/regions", params={"per_page": 100})
    regions = [r for r in regions_raw if isinstance(r, dict)]

    sizes_raw = _collect_paginated(token, "/sizes", params={"per_page": 100})
    sizes = [s for s in sizes_raw if isinstance(s, dict)]

    images_raw = _collect_paginated(
        token,
        "/images",
        params={"type": "distribution", "per_page": 100},
    )
    images = [i for i in images_raw if isinstance(i, dict)]

    return {"regions": regions, "sizes": sizes, "images": images}
