import math
import os
from typing import Union

import stripe
from capyc.core.i18n import translation
from capyc.rest_framework.exceptions import PaymentException, ValidationException
from django.contrib.auth.models import User
from django.utils import timezone
from traitlets import Callable

from breathecode.authenticate.models import Academy, UserSetting
from breathecode.payments.models import (
    AcademyPaymentSettings,
    Bag,
    Currency,
    FinancialReputation,
    Invoice,
    PaymentContact,
)
from breathecode.utils import getLogger

logger = getLogger(__name__)

__all__ = ["Stripe"]


class Stripe:
    """
    Stripe Service.

    This class provides an interface to interact with the Stripe API for various
    payment-related operations such as creating card tokens, managing payment methods,
    handling customer contacts, processing payments, issuing refunds, and creating
    payment links.

    It handles Stripe API key management, allowing for academy-specific keys or
    a general key from environment variables. It also includes internationalization
    for error messages.

    Attributes:
        api_key (str): The Stripe API key to be used for requests.
        language (str): The language code (e.g., 'en', 'es') for error messages.
        price_id (str): (Note: This attribute is declared but not used in the provided selection.
                         It might be intended for future use or is a remnant.)
    """

    api_key: str
    language: str
    academy: Union[Academy, None]

    def __init__(self, api_key: Union[str, None] = None, academy: Union[Academy, None] = None) -> None:
        """
        Initializes the Stripe service.

        The API key is determined in the following order of precedence:
        1. `api_key` parameter if provided.
        2. Academy-specific `pos_api_key` from `AcademyPaymentSettings` if `academy` is provided
           and `api_key` is not.
        3. `STRIPE_API_KEY` environment variable as a fallback.

        Args:
            api_key (str, optional): The Stripe API key. Defaults to None.
            academy (Academy, optional): The academy instance to fetch specific payment settings.
                                         Defaults to None.
        """
        self.api_key = api_key
        self.language = "en"  # Default language
        self.academy = academy

        # If academy is provided and no explicit api_key, try to get academy-specific settings
        if academy and not api_key:
            academy_settings = AcademyPaymentSettings.objects.filter(academy=academy).only("pos_api_key").first()
            if academy_settings:
                self.api_key = academy_settings.pos_api_key

        # Fallback to environment variable if no api_key is set yet
        if not self.api_key:
            self.api_key = os.getenv("STRIPE_API_KEY")

    def set_language(self, lang: str) -> None:
        """
        Sets the language for internationalized error messages.

        Args:
            lang (str): The language code (e.g., 'en', 'es').
        """
        self.language = lang

    def set_language_from_settings(self, settings: UserSetting):
        """
        Sets the language for error messages based on user settings.

        Args:
            settings (UserSetting): The UserSetting object containing the language preference.
        """
        self.language = settings.lang

    def create_card_token(self, card_number: str, exp_month: int, exp_year: int, cvc: str) -> str:
        """
        Creates a Stripe card token from card details.

        This token can be used to create a charge or to save the card details to a customer.

        Args:
            card_number (str): The card number.
            exp_month (int): The card's expiration month (1-12).
            exp_year (int): The card's expiration year (e.g., 2025).
            cvc (str): The card's CVC/CVV code.

        Returns:
            str: The ID of the created Stripe token.

        Raises:
            PaymentException: If there's an issue with card validation or Stripe API communication.
        """
        stripe.api_key = self.api_key

        def callback():
            return stripe.Token.create(
                card={
                    "number": card_number,
                    "exp_month": exp_month,
                    "exp_year": exp_year,
                    "cvc": cvc,
                }
            )

        return self._i18n_validations(callback).id

    def add_payment_method(self, user: User, token: str):
        """
        Adds a payment method (card token) to a Stripe customer.

        If the user doesn't have a Stripe customer record (PaymentContact),
        it creates one first.

        Args:
            user (User): The Django user to whom the payment method will be added.
            token (str): The Stripe card token (e.g., "tok_xxxxxxxx").

        Returns:
            stripe.Customer: The updated Stripe Customer object.

        Raises:
            PaymentException: If there's an issue with Stripe API communication or
                              if the token is invalid.
        """
        stripe.api_key = self.api_key

        contact = PaymentContact.objects.filter(user=user, academy=self.academy).first()
        if not contact:
            contact = self.add_contact(user)

        def callback():
            return stripe.Customer.modify(contact.stripe_id, source=token)

        return self._i18n_validations(callback)

    def add_contact(self, user: User) -> PaymentContact:
        """
        Creates or retrieves a Stripe customer (PaymentContact) for a given user.

        If a PaymentContact already exists for the user, it's returned.
        Otherwise, a new Stripe customer is created, and a corresponding
        PaymentContact record is saved in the database. A FinancialReputation
        record is also ensured for the user.

        Args:
            user (User): The Django user for whom to create/retrieve the contact.

        Returns:
            PaymentContact: The PaymentContact instance linked to the Stripe customer.

        Raises:
            PaymentException: If there's an issue with Stripe API communication.
        """
        stripe.api_key = self.api_key

        if contact := PaymentContact.objects.filter(user=user, academy=self.academy).first():
            return contact

        contact = PaymentContact(user=user, academy=self.academy)

        name = user.first_name
        name += f" {user.last_name}" if name and user.last_name else f"{user.last_name}"

        def callback():
            return stripe.Customer.create(email=user.email, name=name)

        response = self._i18n_validations(callback)

        contact.stripe_id = response["id"]
        contact.save()

        FinancialReputation.objects.get_or_create(user=user)

        return contact

    def _execute_callback(self, callback: Callable):
        """
        Executes a given callable.

        This is a helper method primarily used by `_i18n_validations` to wrap
        Stripe API calls.

        Args:
            callback (callable): The function to execute, typically a Stripe API call.

        Returns:
            The result of the callback execution result.
        """
        return callback()

    def _i18n_validations(self, callback: Callable, attempts: int = 0):
        """
        Wraps a Stripe API call to handle common Stripe errors and translate them.

        It attempts retries for API connection errors up to a certain limit.
        Other Stripe-specific errors are caught and re-raised as PaymentException
        with internationalized messages.

        Args:
            callback (callable): The function making the Stripe API call.
            attempts (int, optional): The current number of retry attempts for
                                      APIConnectionError. Defaults to 0.

        Returns:
            The result of the successful callback execution.

        Raises:
            PaymentException: For various Stripe errors (CardError, RateLimitError,
                              InvalidRequestError, AuthenticationError, APIConnectionError,
                              StripeError) or any other unexpected exception, with
                              an internationalized error message.
        """
        try:
            return self._execute_callback(callback)

        except stripe.error.CardError as e:
            logger.error(str(e))
            raise PaymentException(
                translation(self.language, en="Card declined", es="Tarjeta rechazada", slug="card-error"),
                slug="card-error",
                silent=True,
            )

        except stripe.error.RateLimitError as e:
            logger.error(str(e))
            raise PaymentException(
                translation(
                    self.language, en="Too many requests", es="Demasiadas solicitudes", slug="rate-limit-error"
                ),
                slug="rate-limit-error",
                silent=True,
            )

        except stripe.error.InvalidRequestError as e:
            logger.error(str(e))
            raise PaymentException(
                translation(self.language, en="Invalid request", es="Solicitud invalida", slug="invalid-request"),
                slug="invalid-request",
                silent=True,
            )

        except stripe.error.AuthenticationError as e:
            logger.error(str(e))
            raise PaymentException(
                translation(
                    self.language, en="Authentication error", es="Error de autenticación", slug="authentication-error"
                ),
                slug="authentication-error",
                silent=True,
            )

        except stripe.error.APIConnectionError as e:
            attempts += 1
            if attempts < 5:
                return self._i18n_validations(callback, attempts=attempts)

            logger.error(str(e))

            raise PaymentException(
                translation(
                    self.language,
                    en="Payment service are down, try again later",
                    es="El servicio de pago está caído, inténtalo de nuevo más tarde",
                    slug="payment-service-are-down",
                ),
                slug="payment-service-are-down",
                silent=True,
            )

        except stripe.error.StripeError as e:
            logger.error(str(e))
            raise PaymentException(
                translation(
                    self.language,
                    en="We have problems with the payment provider, try again later",
                    es="Tenemos problemas con el proveedor de pago, inténtalo de nuevo más tarde",
                    slug="stripe-error",
                ),
                slug="stripe-error",
                silent=True,
            )

        except Exception as e:
            # Something else happened, completely unrelated to Stripe
            logger.error(str(e))

            raise PaymentException(
                translation(
                    self.language,
                    en="A unexpected error occur during the payment process, please contact support",
                    es="Ocurrió un error inesperado durante el proceso de pago, comuníquese con soporte",
                    slug="unexpected-exception",
                ),
                slug="unexpected-exception",
                silent=True,
            )

    def pay(
        self,
        user: User,
        bag: Bag,
        amount: int | float,
        currency: str | Currency = "usd",
        description: str = "",
    ) -> Invoice:
        """
        Processes a payment for a given user and bag.

        This method creates a Stripe charge against the user's default payment method.
        It ensures the user has a Stripe customer record (PaymentContact).
        An Invoice record is created and saved upon successful payment.

        Args:
            user (User): The user making the payment.
            bag (Bag): The bag object representing the purchase.
            amount (int | float): The amount to charge, in the major currency unit (e.g., dollars).
            currency (str | Currency, optional): The currency code (e.g., "usd") or
                                                 a Currency model instance. Defaults to "usd".
            description (str, optional): A description for the charge. Defaults to "".

        Returns:
            Invoice: The created Invoice object after successful payment.

        Raises:
            ValidationException: If the currency cannot be determined.
            PaymentException: If there's an issue with the Stripe charge (e.g., card declined).
        """
        stripe.api_key = self.api_key

        if isinstance(currency, str):
            currency_obj = Currency.objects.filter(code__iexact=currency).first()
            if not currency_obj:
                raise ValidationException(
                    translation(
                        self.language,
                        en="Cannot determine the currency during process of payment",
                        es="No se puede determinar la moneda durante el proceso de pago",
                        slug="currency",
                    ),
                    code=500,
                )
            currency = currency_obj  # Assign the Currency object back

        customer = self.add_contact(user)

        # https://stripe.com/docs/currencies
        # Calculate amount in smallest currency unit (e.g., cents)
        decimals_factor = 1
        for _ in range(currency.decimals):
            decimals_factor *= 10

        # https://stripe.com/docs/api/charges/create
        # Stripe expects amount in cents (or smallest unit)
        amount = math.ceil(amount * decimals_factor)

        def callback():
            return stripe.Charge.create(
                customer=customer.stripe_id,
                amount=amount,  # Use the amount in cents
                currency=currency.code.lower(),
                description=description,
            )

        charge = self._i18n_validations(callback)

        utc_now = timezone.now()
        invoice = Invoice(user=user, amount=amount, stripe_id=charge["id"], paid_at=utc_now, status="FULFILLED")
        invoice.currency = currency
        invoice.bag = bag
        invoice.academy = bag.academy

        invoice.save()

        return invoice

    def refund_payment(self, invoice: Invoice) -> Invoice:
        """
        Refunds a payment associated with a given invoice.

        This method creates a Stripe refund for the charge ID stored in the invoice.
        The invoice status is updated to "REFUNDED", and refund details are saved.

        Args:
            invoice (Invoice): The invoice object representing the payment to be refunded.
                               It must have a `stripe_id` (charge ID).

        Returns:
            Invoice: The updated Invoice object with refund details.

        Raises:
            PaymentException: If there's an issue with the Stripe refund process.
        """
        stripe.api_key = self.api_key

        # Ensure the user associated with the invoice has a contact, though Stripe refund
        # primarily needs the charge ID. This might be for consistency or future use.
        self.add_contact(invoice.user)

        def callback():
            return stripe.Refund.create(charge=invoice.stripe_id)

        refund = self._i18n_validations(callback)

        invoice.refund_stripe_id = refund["id"]
        invoice.refunded_at = timezone.now()
        invoice.status = "REFUNDED"
        invoice.save()

        return invoice

    def create_payment_link(self, price_id: str, quantity: int) -> tuple[str, str]:
        """
        Creates a Stripe Payment Link.

        Payment Links are shareable pages hosted by Stripe that allow customers
        to pay for a product or service.

        Args:
            price_id (str): The ID of the Stripe Price object (e.g., "price_xxxxxxxx").
            quantity (int): The quantity of the item associated with the price.

        Returns:
            tuple[str, str]: A tuple containing the ID of the created Payment Link
                             and its URL.

        Raises:
            PaymentException: If there's an issue with the Stripe API communication
                              or if the parameters are invalid.
        """
        stripe.api_key = self.api_key

        def callback():
            return stripe.PaymentLink.create(
                line_items=[
                    {
                        "price": price_id,
                        "quantity": quantity,
                    },
                ],
            )

        payment_link_object = self._i18n_validations(callback)
        return payment_link_object["id"], payment_link_object["url"]
