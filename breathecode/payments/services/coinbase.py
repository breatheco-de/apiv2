import hashlib
import hmac
import os
from typing import Union

import requests
from capyc.core.i18n import translation
from capyc.rest_framework.exceptions import PaymentException, ValidationException

from breathecode.authenticate.models import Academy
from breathecode.payments.models import AcademyPaymentSettings
from breathecode.utils import getLogger

logger = getLogger(__name__)

__all__ = ["CoinbaseCommerce"]


class CoinbaseCommerce:
    api_key: str
    webhook_secret: str
    language: str
    academy: Union[Academy, None]

    def __init__(self, api_key: Union[str, None] = None, academy: Union[Academy, None] = None) -> None:
        """
        Initializes the Coinbase Commerce service.

        The API key and webhook secret are determined in the following order of precedence:
        1. `api_key` parameter if provided.
        2. Academy-specific `coinbase_api_key` and `coinbase_webhook_secret` from
           `AcademyPaymentSettings` if `academy` is provided and `api_key` is not.
        3. `COINBASE_API_KEY` and `COINBASE_WEBHOOK_SECRET` environment variables as fallback.

        Args:
            api_key (str, optional): The Coinbase Commerce API key. Defaults to None.
            academy (Academy, optional): The academy instance to fetch specific payment settings.
                                        Defaults to None.
        """
        self.api_key = api_key
        self.webhook_secret = None
        self.language = "en"  # Default language
        self.academy = academy

        # If academy is provided and no explicit api_key, try to get academy-specific settings
        if academy and not api_key:
            academy_settings = (
                AcademyPaymentSettings.objects.filter(academy=academy)
                .only("coinbase_api_key", "coinbase_webhook_secret")
                .first()
            )
            if academy_settings:
                self.api_key = academy_settings.coinbase_api_key
                self.webhook_secret = academy_settings.coinbase_webhook_secret

        # Fallback to environment variables if no api_key is set yet
        if not self.api_key:
            self.api_key = os.getenv("COINBASE_API_KEY")

        if not self.webhook_secret:
            self.webhook_secret = os.getenv("COINBASE_WEBHOOK_SECRET")

    def set_language(self, lang: str) -> None:
        """
        Sets the language for internationalized error messages.

        Args:
            lang (str): The language code (e.g., 'en', 'es').
        """
        self.language = lang

    def create_charge(self, bag, amount, metadata, return_url, cancel_url):
        """
        Create a Coinbase Commerce charge for a payment.

        Args:
            bag (Bag): The shopping bag being purchased
            amount (float): The amount to charge in the bag's currency
            metadata (dict): Metadata to attach to the charge. Should include:
                - bag_id (int): ID of the bag
                - user_id (int): ID of the user making the payment
                - amount (str): Amount as string
                - original_price (float): Original price before discounts
                - chosen_period (str): Subscription period (MONTH, QUARTER, etc.)
                - is_recurrent (bool): Whether this is a recurring payment
                - subscription_id (int, optional): Only for renewal flows
                - plan_financing_id (int, optional): Only for plan financing renewal flows
            return_url (str): URL to redirect user after successful payment
            cancel_url (str): URL to redirect user if payment is cancelled
        """

        if not self.api_key:
            logger.error(f"CoinbaseCommerce: Coinbase API key not configured for academy {bag.academy.id}")
            raise ValidationException(
                translation(
                    self.language,
                    en="Coinbase Commerce is not configured for this academy. Please contact support.",
                    es="Coinbase Commerce no está configurado para esta academia. Por favor contacta a soporte.",
                    slug="coinbase-not-configured",
                ),
                code=500,
            )

        headers = {
            "Content-Type": "application/json",
            "X-CC-Api-Key": self.api_key,
        }
        description = f"Purchase at {bag.academy.name}"
        charge_body = {
            "name": f"Order {bag.id}",
            "description": description,
            "pricing_type": "fixed_price",
            "local_price": {
                "amount": "0.001",
                "currency": bag.currency.code,
            },
            "metadata": metadata,
            "redirect_url": return_url,
            "cancel_url": cancel_url,
        }
        logger.info(
            f"CoinbaseCommerce: Calling Coinbase API - "
            f"amount={charge_body['local_price']['amount']}, "
            f"currency={charge_body['local_price']['currency']}, "
            f"bag_id={bag.id}"
        )
        response = requests.post("https://api.commerce.coinbase.com/charges", headers=headers, json=charge_body)
        logger.info(f"CoinbaseCommerce: Coinbase API response status: {response.status_code}")

        if response.status_code != 201:
            error_msg = "Unknown error"
            try:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", response.text)
                logger.error(f"CoinbaseCommerce: Coinbase API error - status={response.status_code}, error={error_msg}")
            except Exception:
                error_msg = response.text
                logger.error(
                    f"CoinbaseCommerce: Coinbase API error (non-JSON) - "
                    f"status={response.status_code}, response={error_msg}"
                )

            raise PaymentException(
                translation(
                    self.language,
                    en=f"Error creating Coinbase charge: {error_msg}",
                    es=f"Error creando cargo de Coinbase: {error_msg}",
                    slug="coinbase-charge-error",
                ),
                code=400,
            )
        charge = response.json()
        charge_data = charge.get("data", {})
        return charge_data

    def get_charge(self, charge_id: str) -> dict:
        """
        Retrieve a charge from Coinbase Commerce by its ID.

        Args:
            charge_id (str): The Coinbase charge ID to retrieve.

        Returns:
            dict: The charge data from Coinbase.

        Raises:
            PaymentException: If the charge cannot be retrieved.
        """
        if not self.api_key:
            raise ValidationException(
                translation(
                    self.language,
                    en="Coinbase Commerce is not configured",
                    es="Coinbase Commerce no está configurado",
                ),
                slug="coinbase-not-configured",
                code=500,
            )

        try:
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-CC-Api-Key": self.api_key,
            }
            response = requests.get(
                f"https://api.commerce.coinbase.com/charges/{charge_id}",
                headers=headers,
            )

            if response.status_code != 200:
                error_msg = "Unknown error"
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", response.text)
                except Exception:
                    error_msg = response.text

                logger.error(
                    f"CoinbaseCommerce: Error retrieving charge {charge_id} - "
                    f"status={response.status_code}, error={error_msg}"
                )
                raise PaymentException(
                    translation(
                        self.language,
                        en=f"Error retrieving charge: {error_msg}",
                        es=f"Error obteniendo cargo: {error_msg}",
                    ),
                    code=response.status_code,
                )

            charge_data = response.json()
            charge = charge_data.get("data")
            return charge

        except PaymentException:
            raise
        except Exception as e:
            logger.error(f"CoinbaseCommerce: Unexpected error getting charge {charge_id} - {str(e)}")
            raise PaymentException(
                translation(
                    self.language,
                    en=f"Error retrieving charge {charge_id}",
                    es=f"Error obteniendo cargo {charge_id}",
                ),
                code=500,
            )

    def verify_webhook_signature(self, signature: str, payload: bytes) -> bool:
        """
        Verify webhook signature from Coinbase Commerce.

        Args:
            signature (str): X-CC-Webhook-Signature header value
            payload (bytes): Raw request body

        Returns:
            bool: True if signature is valid

        Raises:
            ValidationException: If signature is invalid
        """
        if not self.webhook_secret:
            raise ValidationException(
                translation(
                    self.language,
                    en="Webhook secret not configured",
                    es="Secreto de webhook no configurado",
                ),
                slug="webhook-secret-missing",
            )

        computed_signature = hmac.new(self.webhook_secret.encode(), payload, hashlib.sha256).hexdigest()

        return hmac.compare_digest(computed_signature, signature)
