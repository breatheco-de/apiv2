import logging
from typing import Any, Dict, Optional

import requests

from breathecode.admissions.models import Academy
from breathecode.provisioning.models import ProvisioningAcademy

logger = logging.getLogger(__name__)


class LiteLLMError(Exception):
    """Raised when the LiteLLM API returns an error or the request fails."""

    pass


class LiteLLMClient:
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        *,
        academy: Optional[Academy] = None,
    ):
        """
        Initialize the client either with explicit base_url/api_key or by resolving
        them from ProvisioningAcademy for the given academy.
        """
        if base_url and api_key:
            self.base_url = base_url.rstrip("/")
            self.api_key = api_key
            return

        if not academy:
            raise ValueError("Either (base_url & api_key) or academy must be provided")

        provisioning_academy = ProvisioningAcademy.objects.select_related("vendor").filter(academy=academy).first()
        if not provisioning_academy:
            raise ValueError("ProvisioningAcademy config not found for this academy/vendor")

        if not provisioning_academy.credentials_token:
            raise ValueError("ProvisioningAcademy missing credentials_token for LLM provider")

        if not provisioning_academy.vendor or not provisioning_academy.vendor.api_url:
            raise ValueError("ProvisioningVendor missing api_url for LLM provider")

        self.base_url = provisioning_academy.vendor.api_url.rstrip("/")
        self.api_key = provisioning_academy.credentials_key
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _extract_error_message(resp: requests.Response) -> str:
        """
        Try to extract a useful error message from a LiteLLM (FastAPI-style) error response.
        """
        message = resp.text[:300]
        try:
            error_data = resp.json()
            detail = error_data.get("detail")
            if isinstance(detail, list) and detail:
                first = detail[0]
                if isinstance(first, dict):
                    msg = first.get("msg")
                    if msg:
                        message = msg
            elif isinstance(detail, str):
                message = detail
        except ValueError:
            # Response is not JSON; keep the raw text snippet
            pass

        return message

    def create_api_key(
        self,
        external_user_id: str,
        name: Optional[str] = None,
        timeout: float = 10.0,
    ) -> Dict[str, Any]:
        """
        Create a new API key for the given external_user_id in LiteLLM.

        Returns a normalized dict, e.g.:
        {
            "id": "<token_id>",        # stable id in LiteLLM
            "key": "<plaintext_key>",  # only shown once; do NOT log/persist in clear text
            "name": "<alias>",         # optional label
            "created_at": "...",       # ISO8601 if LiteLLM returns it
        }
        """
        url = f"{self.base_url.rstrip('/')}/key/generate"

        payload: Dict[str, Any] = {
            "user_id": external_user_id,
            "duration": "30d",
            "key_alias": name,
        }

        try:
            resp = requests.post(url, headers=self.headers, json=payload, timeout=timeout)
        except requests.RequestException as exc:
            raise LiteLLMError(f"Error calling LiteLLM to create API key: {exc}") from exc

        if resp.status_code >= 400:
            message = self._extract_error_message(resp)
            raise LiteLLMError(f"Failed to create LiteLLM API key ({resp.status_code}): {message}")

        data: Dict[str, Any] = resp.json()

        return {
            "id": data.get("token_id"),
            "key": data.get("key"),
            "name": data.get("key_alias"),
            "created_at": data.get("created_at"),
        }

    def regenerate_api_key(
        self,
        user_id: str,
        token_id: str,
        timeout: float = 10.0,
    ) -> Dict[str, Any]:
        """
        Regenerate an existing API key for the given user.

        Returns a normalized dict with the new key:
        {
            "id": "<token_id>",
            "key": "<plaintext_key>",
            "name": "<alias>",
            "created_at": "...",
        }
        """
        url = f"{self.base_url.rstrip('/')}/key/regenerate"

        payload: Dict[str, Any] = {
            "user_id": user_id,
            "token_id": token_id,
        }

        try:
            resp = requests.post(url, headers=self.headers, json=payload, timeout=timeout)
        except requests.RequestException as exc:
            raise LiteLLMError(f"Error calling LiteLLM to regenerate API key: {exc}") from exc

        if resp.status_code >= 400:
            message = self._extract_error_message(resp)
            raise LiteLLMError(f"Failed to regenerate LiteLLM API key ({resp.status_code}): {message}")

        data: Dict[str, Any] = resp.json()

        return {
            "id": data.get("token_id"),
            "key": data.get("key"),
            "name": data.get("key_alias"),
            "created_at": data.get("created_at"),
        }

    def delete_api_keys(
        self,
        user_id: str,
        token_ids: list[str] = None,
        timeout: float = 10.0,
    ) -> bool:
        """
        Delete one or more API keys for the given user.

        Returns True if the operation succeeded (2xx status).
        """
        url = f"{self.base_url.rstrip('/')}/key/delete"
        payload: Dict[str, Any] = {
            "keys": token_ids,
        }

        try:
            resp = requests.post(url, headers=self.headers, json=payload, timeout=timeout)
        except requests.RequestException as exc:
            raise LiteLLMError(f"Error calling LiteLLM to delete API keys: {exc}") from exc

        if resp.status_code >= 400:
            message = self._extract_error_message(resp)
            raise LiteLLMError(f"Failed to delete LiteLLM API keys ({resp.status_code}): {message}")

        return True

    def get_user_info(
        self,
        user_id: str,
        timeout: float = 10.0,
    ) -> Dict[str, Any]:
        """
        Get LiteLLM user information (including usage) for the given user_id.

        Sends the user_id in the querystring, as expected by LiteLLM.
        Returns the raw JSON response from LiteLLM.
        """
        url = f"{self.base_url.rstrip('/')}/user/info"

        try:
            resp = requests.get(
                url,
                headers=self.headers,
                params={"user_id": user_id},
                timeout=timeout,
            )
        except requests.RequestException as exc:
            raise LiteLLMError(f"Error calling LiteLLM to get user info: {exc}") from exc

        if resp.status_code >= 400:
            message = self._extract_error_message(resp)
            raise LiteLLMError(f"Failed to get LiteLLM user info ({resp.status_code}): {message}")

        return resp.json()

    def delete_user(
        self,
        user_ids: list[str],
        timeout: float = 10.0,
    ) -> bool:
        """
        Delete one or more LiteLLM users and all of their API keys.

        Returns True if the operation succeeded (2xx status).
        """
        url = f"{self.base_url.rstrip('/')}/user/delete"

        payload: Dict[str, Any] = {
            "user_ids": user_ids,
        }

        try:
            resp = requests.post(url, headers=self.headers, json=payload, timeout=timeout)
        except requests.RequestException as exc:
            raise LiteLLMError(f"Error calling LiteLLM to delete user: {exc}") from exc

        if resp.status_code >= 400:
            message = self._extract_error_message(resp)
            raise LiteLLMError(f"Failed to delete LiteLLM user(s) ({resp.status_code}): {message}")

        return True
