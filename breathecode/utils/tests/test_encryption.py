"""Tests for breathecode.utils.encryption."""

import pytest
from django.test import override_settings

from breathecode.utils.encryption import decrypt, encrypt, get_fernet_key


@pytest.mark.django_db
class TestEncryption:
    def test_get_fernet_key_returns_bytes(self):
        with override_settings(ENCRYPTION_SECRET_KEY="test-secret-key-32-chars!!"):
            key = get_fernet_key()
            assert isinstance(key, bytes)
            assert len(key) > 0

    def test_encrypt_decrypt_round_trip(self):
        with override_settings(ENCRYPTION_SECRET_KEY="test-secret-key-32-chars!!"):
            plain = "my-secret-password"
            cipher = encrypt(plain)
            assert cipher != plain
            assert decrypt(cipher) == plain

    def test_encrypt_empty_returns_empty(self):
        with override_settings(ENCRYPTION_SECRET_KEY="test-secret-key-32-chars!!"):
            assert encrypt("") == ""
            assert encrypt(None) == ""

    def test_decrypt_empty_returns_empty(self):
        with override_settings(ENCRYPTION_SECRET_KEY="test-secret-key-32-chars!!"):
            assert decrypt("") == ""
            assert decrypt(None) == ""
