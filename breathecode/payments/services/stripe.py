import os
import stripe

from breathecode.payments.models import Invoice, PaymentContact
from breathecode.utils import getLogger
from django.contrib.auth.models import User
from breathecode.utils import PaymentException, ValidationException

logger = getLogger(__name__)


class Stripe:
    api_key: str

    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv('STRIPE_API_KEY')

    def create_card_token(self, card_number: str, exp_month: int, exp_year: int, cvc: str):
        stripe.api_key = self.api_key

        token = stripe.Token.create(card={
            'number': card_number,
            'exp_month': exp_month,
            'exp_year': exp_year,
            'cvc': cvc,
        })
        return token.id

    def add_payment_method(self, user: User, token: str, attempts=0):
        stripe.api_key = self.api_key

        contact = PaymentContact.objects.filter(user=user).first()
        if not contact:
            contact = self.add_contact(user)

        try:
            stripe.Customer.modify(contact.stripe_id, source=token)

        except stripe.error.CardError as e:
            logger.error(str(e))
            raise PaymentException('Card declined', slug='card-error')

        except stripe.error.RateLimitError as e:
            logger.error(str(e))
            raise PaymentException('Too many requests', slug='rate-limit-error')

        except stripe.error.InvalidRequestError as e:
            logger.error(str(e))
            raise ValidationException(str(e), code=400, slug='invalid-request')

        except stripe.error.AuthenticationError as e:
            logger.error(str(e))
            raise ValidationException(str(e), code=400, slug='authentication-error')

        except stripe.error.APIConnectionError as e:
            attempts += 1
            if attempts < 5:
                return self.add_payment_method(user, token, attempts=attempts)

            logger.error(str(e))
            raise ValidationException(str(e), code=500, slug='payment-service-are-down')

        except stripe.error.StripeError as e:
            logger.error(str(e))
            raise PaymentException(str(e), slug='error')

        except Exception as e:
            # Something else happened, completely unrelated to Stripe
            logger.error(str(e))
            raise PaymentException('A unexpected error occur in the server', slug='unexpected-exception')

    def add_contact(self, user: User):
        stripe.api_key = self.api_key

        if contact := PaymentContact.objects.filter(user=user).first():
            return contact

        contact = PaymentContact(user=user)

        name = user.first_name
        name += f' {user.last_name}' if name and user.last_name else f'{user.last_name}'

        response = stripe.Customer.create(email=user.email, name=name)
        contact.stripe_id = response.id
        contact.save()

        return contact

    def pay(self, user: User, amount: float, description: str = '') -> Invoice:
        stripe.api_key = self.api_key

        customer = self.add_contact(user)

        # create a charge in stripe using the customer and the amount
        charge = stripe.Charge.create(customer=customer.id,
                                      amount=amount,
                                      currency='usd',
                                      description=description)

        #TODO: think about ban a user if have bad reputation (FinancialReputation)
        payment = Invoice(user=user, amount=amount, stripe_id=charge.id)
        payment.status = 'FULFILLED'
        #   status='FULFILLED' if successfully else 'REJECTED',

        payment.save()

        # return a json with the payment data
        return payment
