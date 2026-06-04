import logging
import os

import requests

from capyc.rest_framework.exceptions import ValidationException

logger = logging.getLogger(__name__)

__all__ = ["Turnstile"]


class Turnstile:
    """Cloudflare Turnstile CAPTCHA service"""

    VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"

    def __init__(self):
        """Initialize Turnstile service"""
        pass

    def verify_token(self, secret_key: str, token: str, remoteip: str = None) -> dict:
        """Verify a Turnstile token with Cloudflare's API.

        Args:
            secret_key: Cloudflare Turnstile secret key
            token: The token obtained from the client
            remoteip: Optional IP address of the user

        Returns:
            dict: Response from Cloudflare API containing success status and error codes

        Raises:
            ValidationException: If token verification fails
        """
        if not secret_key:
            raise ValidationException("Cloudflare Turnstile secret key is not configured", code=500)

        if not token:
            raise ValidationException("Missing Turnstile token", code=400)

        payload = {
            "secret": secret_key,
            "response": token,
        }

        if remoteip:
            payload["remoteip"] = remoteip

        try:
            response = requests.post(self.VERIFY_URL, data=payload, timeout=10)
            response.raise_for_status()
            result = response.json()

            if not result.get("success", False):
                error_codes = result.get("error-codes", [])
                error_message = "Turnstile verification failed"
                if error_codes:
                    error_message += f": {', '.join(error_codes)}"
                logger.error(f"Turnstile verification failed: {error_codes}")
                raise ValidationException(error_message, code=400)

            logger.info("Turnstile token verified successfully")
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling Cloudflare Turnstile API: {str(e)}")
            raise ValidationException("Failed to verify Turnstile token", code=500)
        except ValueError as e:
            logger.error(f"Invalid JSON response from Cloudflare Turnstile API: {str(e)}")
            raise ValidationException("Invalid response from Turnstile service", code=500)

