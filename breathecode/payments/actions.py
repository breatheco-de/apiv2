import os
import stripe
from .models import Invoice


def payWithStripe(
    request,
    user,
):
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

    # create a charge in stripe using the customer and the amount
    charge = stripe.Charge.create(customer=customer.id,
                                  amount=amount,
                                  currency='usd',
                                  description=description)

    # create a payment object and save it in the database
    payment = Invoice(user=user, amount=amount, description=description, stripe_id=charge.id)
    payment.save()

    # return a json with the payment data
    return JsonResponse(payment.to_dict())
