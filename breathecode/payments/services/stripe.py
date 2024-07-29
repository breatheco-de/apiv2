import math
import os

import stripe
from django.contrib.auth.models import User
from django.utils import timezone

from breathecode.authenticate.models import UserSetting
from breathecode.payments.models import Bag, Currency, FinancialReputation, Invoice, PaymentContact
from breathecode.utils import getLogger
from breathecode.utils.i18n import translation
from capyc.rest_framework.exceptions import PaymentException, ValidationException

logger = getLogger(__name__)

__all__ = ["Stripe"]


class Stripe:
    """Stripe service."""

    api_key: str
    language: str

    def __init__(self, api_key=None) -> None:
        self.api_key = api_key or os.getenv("STRIPE_API_KEY")
        self.language = "en"

    def set_language(self, lang: str) -> None:
        """Set the language for the error messages."""
        self.language = lang

    def set_language_from_settings(self, settings: UserSetting):
        """Set the language for the error messages."""

        self.language = settings.lang

    def create_card_token(self, card_number: str, exp_month: int, exp_year: int, cvc: str) -> None:
        """Create a card token to be used in the payment process."""

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
        """Add a payment method to the user."""

        stripe.api_key = self.api_key

        contact = PaymentContact.objects.filter(user=user).first()
        if not contact:
            contact = self.add_contact(user)

        def callback():
            return stripe.Customer.modify(contact.stripe_id, source=token)

        return self._i18n_validations(callback)

    def add_contact(self, user: User):
        """Add a contact to the user."""

        stripe.api_key = self.api_key

        if contact := PaymentContact.objects.filter(user=user).first():
            return contact

        contact = PaymentContact(user=user)

        name = user.first_name
        name += f" {user.last_name}" if name and user.last_name else f"{user.last_name}"

        def callback():
            return stripe.Customer.create(email=user.email, name=name)

        response = self._i18n_validations(callback)

        contact.stripe_id = response["id"]
        contact.save()

        FinancialReputation.objects.get_or_create(user=user)

        return contact

    def _execute_callback(self, callback: callable):
        return callback()

    def _i18n_validations(self, callback: callable, attempts=0):
        """Translate the error messages from stripe to the user language."""

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
        amount: int,
        currency: str | Currency = "usd",
        description: str = "",
    ) -> Invoice:
        """Pay for a given bag."""

        stripe.api_key = self.api_key

        if isinstance(currency, str):
            currency = Currency.objects.filter(code=currency).first()
            if not currency:
                raise ValidationException(
                    translation(
                        self.language,
                        en="Cannot determine the currency during process of payment",
                        es="No se puede determinar la moneda durante el proceso de pago",
                        slug="currency",
                    ),
                    code=500,
                )

        customer = self.add_contact(user)

        # https://stripe.com/docs/currencies
        decimals = 1

        for _ in range(currency.decimals):
            decimals *= 10

        # https://stripe.com/docs/api/charges/create
        stripe_amount = math.ceil(amount * decimals)
        invoice_amount = math.ceil(amount)

        def callback():
            return stripe.Charge.create(
                customer=customer.stripe_id,
                amount=math.ceil(stripe_amount),
                currency=currency.code.lower(),
                description=description,
            )

        charge = self._i18n_validations(callback)

        utc_now = timezone.now()
        invoice = Invoice(user=user, amount=invoice_amount, stripe_id=charge["id"], paid_at=utc_now)
        invoice.status = "FULFILLED"
        invoice.currency = currency
        invoice.bag = bag
        invoice.academy = bag.academy

        invoice.save()

        return invoice

    def refund_payment(self, invoice: Invoice) -> Invoice:
        """Refund a given invoice."""

        stripe.api_key = self.api_key

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
        """Create a payment link for a given price id, return the id and the url."""

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

        refund = self._i18n_validations(callback)

        return refund["id"], refund["url"]
