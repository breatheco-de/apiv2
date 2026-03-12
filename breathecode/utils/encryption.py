"""
Shared encryption utility for sensitive fields (e.g. VPS root password).

Uses ENCRYPTION_SECRET_KEY from Django settings and Fernet (symmetric encryption).
Rotating ENCRYPTION_SECRET_KEY invalidates existing encrypted values unless re-encrypted.
"""

import base64
import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

_fernet_instance = None


def get_fernet_key():
    """Derive a valid Fernet key (32 bytes, base64url) from ENCRYPTION_SECRET_KEY."""
    from django.conf import settings

    secret = getattr(settings, "ENCRYPTION_SECRET_KEY", "") or ""
    if not secret:
        logger.warning("ENCRYPTION_SECRET_KEY is not set; encryption will fail.")
    digest = hashlib.sha256(secret.encode()).digest()
    return base64.urlsafe_b64encode(digest)


def _get_fernet():
    """Lazy-initialized Fernet instance."""
    global _fernet_instance
    if _fernet_instance is None:
        key = get_fernet_key()
        _fernet_instance = Fernet(key)
    return _fernet_instance


def encrypt(plaintext: str) -> str:
    """
    Encrypt a string. Returns base64-encoded ciphertext.
    Raises if ENCRYPTION_SECRET_KEY is missing or invalid.
    """
    if plaintext is None or plaintext == "":
        return ""
    f = _get_fernet()
    token = f.encrypt(plaintext.encode("utf-8"))
    return token.decode("ascii")


def decrypt(ciphertext: str) -> str:
    """
    Decrypt a string produced by encrypt(). Returns plaintext.
    Returns empty string for None or empty input.
    Raises InvalidToken if ciphertext is tampered or key changed.
    """
    if ciphertext is None or ciphertext == "":
        return ""
    f = _get_fernet()
    try:
        decrypted = f.decrypt(ciphertext.encode("ascii"))
        return decrypted.decode("utf-8")
    except InvalidToken as e:
        logger.warning("Decryption failed (wrong key or tampered data): %s", e)
        raise
