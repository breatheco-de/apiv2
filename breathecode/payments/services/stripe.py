import os
from typing import Optional

import stripe
from django.contrib.auth.models import User
from django.utils import timezone

from breathecode.authenticate.models import UserSetting
from breathecode.payments.models import Currency, FinancialReputation, Invoice, PaymentContact
from breathecode.utils import PaymentException, ValidationException, getLogger
from breathecode.utils.i18n import translation
import math

logger = getLogger(__name__)


class Stripe:
    api_key: str
    language: str

    def __init__(self, api_key=None) -> None:
        self.api_key = api_key or os.getenv('STRIPE_API_KEY')
        self.language = 'en'

    def set_language(self, lang: str) -> None:
        self.language = lang

    def set_language_from_settings(self, settings: UserSetting):
        self.language = settings.lang

    def create_card_token(self, card_number: str, exp_month: int, exp_year: int, cvc: str) -> None:
        stripe.api_key = self.api_key

        token = stripe.Token.create(card={
            'number': card_number,
            'exp_month': exp_month,
            'exp_year': exp_year,
            'cvc': cvc,
        })
        return token.id

    def add_payment_method(self, user: User, token: str):
        stripe.api_key = self.api_key

        contact = PaymentContact.objects.filter(user=user).first()
        if not contact:
            contact = self.add_contact(user)

        def callback():
            # return stripe.Customer.create_source(contact.stripe_id, source=token)
            stripe.Customer.modify(contact.stripe_id, source=token)

        return self._i18n_validations(callback)

    def add_contact(self, user: User):
        stripe.api_key = self.api_key

        if contact := PaymentContact.objects.filter(user=user).first():
            return contact

        contact = PaymentContact(user=user)

        name = user.first_name
        name += f' {user.last_name}' if name and user.last_name else f'{user.last_name}'

        response = stripe.Customer.create(email=user.email, name=name)
        contact.stripe_id = response['id']
        contact.save()

        FinancialReputation.objects.get_or_create(user=user)

        return contact

    def _i18n_validations(self, callback: callable, attempts=0):
        try:
            return callback()

        except stripe.error.CardError as e:
            logger.error(str(e))
            raise PaymentException(
                translation(self.language, en='Card declined', es='Tarjeta rechazada', slug='card-error'))

        except stripe.error.RateLimitError as e:
            logger.error(str(e))
            raise PaymentException(
                translation(self.language,
                            en='Too many requests',
                            es='Demasiadas solicitudes',
                            slug='rate-limit-error'))

        except stripe.error.InvalidRequestError as e:
            logger.error(str(e))
            raise PaymentException(
                translation(self.language,
                            en='Invalid request',
                            es='Solicitud invalida',
                            slug='invalid-request'))

        except stripe.error.AuthenticationError as e:
            logger.error(str(e))
            raise PaymentException(
                translation(self.language,
                            en='Authentication error',
                            es='Error de autenticación',
                            slug='authentication-error'))

        except stripe.error.APIConnectionError as e:
            attempts += 1
            if attempts < 5:
                return self._i18n_validations(callback, attempts=attempts)

            logger.error(str(e))

            raise PaymentException(
                translation(self.language,
                            en='Payment service are down, try again later',
                            es='El servicio de pago está caído, inténtalo de nuevo más tarde',
                            slug='payment-service-are-down'))

        except stripe.error.StripeError as e:
            logger.error(str(e))
            raise PaymentException(
                translation(self.language,
                            en='We have problems with the payment provider, try again later',
                            es='Tenemos problemas con el proveedor de pago, inténtalo de nuevo más tarde',
                            slug='stripe-error'))

        except Exception as e:
            # Something else happened, completely unrelated to Stripe
            logger.error(str(e))

            raise PaymentException(
                translation(
                    self.language,
                    en='A unexpected error occur during the payment process, please contact support',
                    es='Ocurrió un error inesperado durante el proceso de pago, comuníquese con soporte',
                    slug='unexpected-exception'))

    def pay(self,
            user: User,
            amount: int,
            currency: str | Currency = 'usd',
            description: str = '') -> Invoice:

        stripe.api_key = self.api_key

        if isinstance(currency, str):
            currency = Currency.objects.filter(code=currency).first()
            if not currency:
                raise ValidationException(translation(
                    self.language,
                    en='Cannot determine the currency during process of payment',
                    es='No se puede determinar la moneda durante el proceso de pago',
                    slug='currency'),
                                          code=500)

        customer = self.add_contact(user)

        def callback():
            return stripe.Charge.create(customer=customer.stripe_id,
                                        amount=math.ceil(amount),
                                        currency=currency.code.lower(),
                                        description=description)

        charge = self._i18n_validations(callback)

        utc_now = timezone.now()
        #TODO: think about ban a user if have bad reputation (FinancialReputation)
        payment = Invoice(user=user, amount=amount, stripe_id=charge['id'], paid_at=utc_now)
        payment.status = 'FULFILLED'
        payment.currency = currency
        #   status='FULFILLED' if successfully else 'REJECTED',

        payment.save()

        # return a json with the payment data
        return payment
