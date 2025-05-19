import os
import base64
import json
import time
import hmac
import hashlib
import uuid
from typing import Dict, List, Optional


class FlagManager:
    """Manages generation, validation, and revocation checking of JWT-inspired CTF flags.

    This class provides methods to generate new flags, validate submitted flags,
    and check if a flag has been revoked. It supports both JWT-style flags
    and legacy flag formats.

    Usage Example:
        # Initialize the FlagManager
        # Optionally, provide a dictionary of legacy flags if needed
        # legacy_flags_data = {
        #     "asset_seed_1": ["legacy_flag_A", "legacy_flag_B"],
        #     "asset_seed_2": ["legacy_flag_C"]
        # }
        # flag_manager = FlagManager(legacy_flags=legacy_flags_data)
        flag_manager = FlagManager()

        # Define an asset seed (publicly known for each CTF asset)
        asset_public_seed = "some_unique_asset_identifier"

        # Generate a new flag
        new_flag = flag_manager.generate_flag(asset_public_seed, expires_in=3600)  # Expires in 1 hour
        print(f"Generated Flag: {new_flag}")

        # Validate a submitted flag
        submitted_flag_to_check = new_flag  # Or a flag submitted by a user
        is_valid = flag_manager.validate_flag(submitted_flag_to_check, asset_public_seed)
        print(f"Flag '{submitted_flag_to_check}' is valid: {is_valid}")

        # Validate with revocation check
        revoked_list = [
            {"flag": "some_revoked_flag_string", "flag_id": "some_revoked_id"},
            {"flag": new_flag, "flag_id": flag_manager.extract_flag_id(new_flag)}
        ]
        is_still_valid = flag_manager.validate_flag(submitted_flag_to_check, asset_public_seed, revoked_flags=revoked_list)
        print(f"Flag '{submitted_flag_to_check}' after revocation check: {is_still_valid}")

        # Extract flag ID
        flag_identifier = flag_manager.extract_flag_id(new_flag)
        print(f"Extracted Flag ID: {flag_identifier}")

        # Example with a legacy flag (if legacy_flags_data was provided at initialization)
        # legacy_flag_to_check = "legacy_flag_A"
        # is_legacy_valid = flag_manager.validate_flag(legacy_flag_to_check, "asset_seed_1")
        # print(f"Legacy Flag '{legacy_flag_to_check}' is valid: {is_legacy_valid}")
    """

    def __init__(self, legacy_flags: Dict[str, List[str]] = None):
        """
        Initialize the FlagManager.

        Args:
            legacy_flags (Dict[str, List[str]], optional): Dictionary mapping asset_seed to legacy flags.
        """
        self.PRIVATE_FLAG_SEED = os.getenv("PRIVATE_FLAG_SEED")
        if not self.PRIVATE_FLAG_SEED:
            raise ValueError("PRIVATE_FLAG_SEED environment variable is not set")
        self.legacy_flags = legacy_flags or {}

    @staticmethod
    def _base64url_encode(data: bytes) -> str:
        """Encode data in base64url format."""
        return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")

    @staticmethod
    def _base64url_decode(data: str) -> bytes:
        """Decode base64url-encoded data."""
        data += "=" * (4 - len(data) % 4)
        return base64.urlsafe_b64decode(data)

    def generate_flag(self, asset_seed: str, flag_id: Optional[str] = None, expires_in: Optional[int] = None) -> str:
        """
        Generate a JWT-inspired flag for a CTF asset.

        Args:
            asset_seed (str): Public seed unique to the CTF asset.
            flag_id (str, optional): Unique identifier for the flag. Defaults to UUID.
            expires_in (int, optional): Seconds until flag expires. Defaults to None (no expiration).

        Returns:
            str: Flag in the format FLAG{header.payload.signature}

        Raises:
            ValueError: If asset_seed is empty.
        """
        if not asset_seed:
            raise ValueError("Asset seed cannot be empty")

        flag_id = flag_id or str(uuid.uuid4())

        # Header
        header = {"alg": "HS256", "typ": "FLAG"}
        header_b64 = self._base64url_encode(json.dumps(header).encode("utf-8"))

        # Payload
        current_time = int(time.time())
        payload = {"asset_seed": asset_seed, "flag_id": flag_id, "iat": current_time}
        if expires_in is not None:
            payload["exp"] = current_time + expires_in
        payload_b64 = self._base64url_encode(json.dumps(payload).encode("utf-8"))

        # Signature
        signing_input = f"{header_b64}.{payload_b64}"
        signature = hmac.new(
            key=self.PRIVATE_FLAG_SEED.encode("utf-8"), msg=signing_input.encode("utf-8"), digestmod=hashlib.sha256
        ).digest()
        signature_b64 = self._base64url_encode(signature)

        return f"FLAG{{{header_b64}.{payload_b64}.{signature_b64}}}"

    def validate_flag(self, submitted_flag: str, asset_seed: str, revoked_flags: List[Dict[str, str]] = None) -> bool:
        """
        Validate a submitted flag against approved flags or JWT signature.

        Args:
            submitted_flag (str): Flag submitted by the student.
            asset_seed (str): Public seed of the CTF asset.
            revoked_flags (List[Dict[str, str]], optional): List of revoked flags with flag_id.

        Returns:
            bool: True if the flag is valid, False otherwise.
        """
        revoked_flags = revoked_flags or []

        # Check if the flag is a legacy flag
        if asset_seed in self.legacy_flags:
            flag_id = self._derive_flag_id(submitted_flag)
            if submitted_flag in self.legacy_flags[asset_seed]:
                return not self.is_flag_revoked(submitted_flag, flag_id, revoked_flags)

        # Check if the flag is a JWT flag
        if not submitted_flag.startswith("FLAG{") or not submitted_flag.endswith("}"):
            return False

        try:
            flag_content = submitted_flag[5:-1]
            header_b64, payload_b64, signature_b64 = flag_content.split(".")
        except ValueError:
            return False

        try:
            header = json.loads(self._base64url_decode(header_b64).decode("utf-8"))
            payload = json.loads(self._base64url_decode(payload_b64).decode("utf-8"))
        except ValueError:
            return False

        if header.get("alg") != "HS256" or header.get("typ") != "FLAG":
            return False

        if payload.get("asset_seed") != asset_seed:
            return False

        # Check expiration if present
        if "exp" in payload:
            current_time = int(time.time())
            if payload["exp"] < current_time:
                return False

        # Check if revoked
        flag_id = payload.get("flag_id")
        if self.is_flag_revoked(submitted_flag, flag_id, revoked_flags):
            return False

        signing_input = f"{header_b64}.{payload_b64}"
        expected_signature = hmac.new(
            key=self.PRIVATE_FLAG_SEED.encode("utf-8"), msg=signing_input.encode("utf-8"), digestmod=hashlib.sha256
        ).digest()
        try:
            submitted_signature = self._base64url_decode(signature_b64)
            return hmac.compare_digest(submitted_signature, expected_signature)
        except (ValueError, TypeError):
            return False

    def is_flag_revoked(self, flag: str, flag_id: str, revoked_flags: List[Dict[str, str]]) -> bool:
        """
        Check if a flag is revoked.

        Args:
            flag (str): The flag to check.
            flag_id (str): The flag_id to check.
            revoked_flags (List[Dict[str, str]]): List of revoked flags with flag_id.

        Returns:
            bool: True if the flag is revoked, False otherwise.
        """
        for revoked in revoked_flags:
            if revoked["flag"] == flag or revoked["flag_id"] == flag_id:
                return True
        return False

    def _derive_flag_id(self, flag: str) -> str:
        """Derive a flag_id for legacy flags (use flag string for simplicity)."""
        return flag
        # Alternative: return hashlib.sha256(flag.encode('utf-8')).hexdigest()[:32]

    def extract_flag_id(self, flag: str) -> Optional[str]:
        """
        Extract the flag_id from a flag string (JWT or legacy).

        Args:
            flag (str): The flag string (e.g., FLAG{header.payload.signature} or legacy flag).

        Returns:
            Optional[str]: The flag_id if extracted, None if invalid.
        """
        # Check if it's a legacy flag
        for _asset_seed, flags in self.legacy_flags.items():
            if flag in flags:
                return self._derive_flag_id(flag)

        # Check if it's a JWT flag
        # Corrected: uses 'flag' instead of 'submitted_flag'
        if not flag.startswith("FLAG{") or not flag.endswith("}"):
            return None
        try:
            payload_b64 = flag[5:-1].split(".")[1]
            payload = json.loads(self._base64url_decode(payload_b64).decode("utf-8"))
            return payload.get("flag_id")
        except (ValueError, IndexError):
            return None
