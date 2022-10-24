import os
import stripe
from dateutil.relativedelta import relativedelta
from .models import Invoice, Subscription


def calculate_renew_delta(subscription: Subscription):
    delta_args = {}
    if subscription.renew_every_unit == 'DAY':
        delta_args['days'] = subscription.renew_every

    elif subscription.renew_every_unit == 'WEEK':
        delta_args['weeks'] = subscription.renew_every

    elif subscription.renew_every_unit == 'MONTH':
        delta_args['months'] = subscription.renew_every

    elif subscription.renew_every_unit == 'YEAR':
        delta_args['years'] = subscription.renew_every

    return relativedelta(**delta_args)


def payWithStripe(request, user) -> Invoice:
    stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

    # get the token from the request
    token = request.POST.get('token')
    # get the amount from the request
    amount = request.POST.get('amount')
    # get the description from the request
    description = request.POST.get('description')

    # get the email from the request
    email = request.POST.get('email')

    # get the user from the request
    user = request.user

    # create a customer in stripe using the token
    customer = stripe.Customer.create(email=email, source=token)
    stripe.Customer.get(customer.id)

    # create a charge in stripe using the customer and the amount
    charge = stripe.Charge.create(customer=customer.id,
                                  amount=amount,
                                  currency='usd',
                                  description=description)

    # create a payment object and save it in the database
    payment = Invoice(user=user, amount=amount, description=description, stripe_id=charge.id)
    #   status='FULFILLED' if successfully else 'REJECTED',

    payment.save()

    # return a json with the payment data
    return payment
