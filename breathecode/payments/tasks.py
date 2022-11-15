import logging
from datetime import datetime

from celery import Task, shared_task

from breathecode.notify import actions as notify_actions
from breathecode.payments import actions
from breathecode.payments.services.stripe import Stripe

from .models import Bag, Consumable, Credit, Invoice, Subscription

logger = logging.getLogger(__name__)


class BaseTaskWithRetry(Task):
    autoretry_for = (Exception, )
    #                                           seconds
    retry_kwargs = {'max_retries': 5, 'countdown': 60 * 5}
    retry_backoff = True


@shared_task(bind=True, base=BaseTaskWithRetry)
def renew_credit(self, subscription_id: int, from_datetime: datetime):
    logger.info(f'Starting renew_credit for subscription {subscription_id}')

    if not (subscription := Subscription.objects.filter(id=subscription_id).first()):
        logger.error(f'Subscription with id {subscription_id} not found')
        return

    subscription.last_renew = from_datetime
    subscription.renew_credits_at = from_datetime + actions.calculate_renew_delta(subscription)

    invoice = subscription.invoices.all().order_by('-created_at').first()

    credit = Credit()
    for service_item in subscription.services.all():
        new_service_credit = Consumable(service=service_item.service,
                                        unit_type=service_item.unit_type,
                                        how_many=service_item.how_many)

        credit.services.add(new_service_credit)

    for plan in subscription.plans.all():
        for service_item in plan.services.all():
            new_service_credit = Consumable(service=service_item.service,
                                            unit_type=service_item.unit_type,
                                            how_many=service_item.how_many)

            credit.services.add(new_service_credit)

    credit.invoice = invoice
    credit.valid_until = subscription.renew_credits_at
    credit.is_free_trial = False
    credit.save()

    subscription.save()

    data = {
        'SUBJECT': 'Your credits has been renewed',
        # 'LINK': f'https://assessment.breatheco.de/{user_assessment.id}?token={token.key}'
    }

    notify_actions.send_email_message('payment', invoice.user.email, data)


@shared_task(bind=True, base=BaseTaskWithRetry)
def renew_subscription(self, subscription_id: int, from_datetime: datetime):
    logger.info(f'Starting renew_subscription for subscription {subscription_id}')

    if not (subscription := Subscription.objects.filter(id=subscription_id).first()):
        logger.error(f'Subscription with id {subscription_id} not found')
        return

    try:
        #FIXME: check what happens if the payment fails
        s = Stripe()
        #TODO: add language to the service
        invoice: Invoice = s.pay(subscription.user)

    except Exception:
        value = invoice.currency.format_price(invoice.amount)

        notify_actions.send_email_message(
            'message',
            invoice.user.email,
            {
                'SUBJECT': 'Your 4Geeks subscription could not be renewed',
                'MESSAGE': f'The amount was {value} but the payment failed',
                'BUTTON': f'See the invoice',
                # 'LINK': f'{APP_URL}/invoice/{instance.id}',
            })

        subscription.status = 'PAYMENT_ISSUE'
        subscription.save()
        return

    subscription.last_renew = from_datetime
    subscription.renew_credits_at = from_datetime + actions.calculate_renew_delta(subscription)

    subscription.invoices.add(invoice)

    # for service in subscription.plan.services.all():
    credit = Credit()
    for service_item in subscription.services.all():
        new_service_credit = Consumable(service=service_item.service,
                                        unit_type=service_item.unit_type,
                                        how_many=service_item.how_many)

        credit.services.add(new_service_credit)

    for plan in subscription.plans.all():
        for service_item in plan.services.all():
            new_service_credit = Consumable(service=service_item.service,
                                            unit_type=service_item.unit_type,
                                            how_many=service_item.how_many)

            credit.services.add(new_service_credit)

    credit.invoice = invoice
    credit.valid_until = subscription.renew_credits_at
    credit.is_free_trial = False
    credit.save()

    subscription.save()
    value = invoice.currency.format_price(invoice.amount)

    notify_actions.send_email_message(
        'message',
        invoice.user.email,
        {
            'SUBJECT': 'Your 4Geeks subscription was successfully renewed',
            'MESSAGE': f'The amount was {value}',
            'BUTTON': f'See the invoice',
            # 'LINK': f'{APP_URL}/invoice/{instance.id}',
        })


@shared_task(bind=True, base=BaseTaskWithRetry)
def build_subscription(self, bag_id: int, invoice_id: int):
    logger.info(f'Starting build_subscription for bag {bag_id}')

    if not (bag := Bag.objects.filter(id=bag_id, status='PAID', was_delivered=False).first()):
        logger.error(f'Bag with id {bag_id} not found')
        return

    if not (invoice := Invoice.objects.filter(id=invoice_id, status='FULFILLED').first()):
        logger.error(f'Invoice with id {invoice_id} not found')
        return

    #TODO: think about Subscription.valid_until
    #FIXME: pay_every
    #FIXME: renew_every
    subscription = Subscription.objects.create(user=bag.user,
                                               plans=bag.plans.all(),
                                               services=bag.services.all(),
                                               is_recurrent=bag.is_recurrent,
                                               paid_at=invoice.paid_at,
                                               status='ACTIVE',
                                               last_renew=invoice.paid_at)

    subscription.save()
    subscription.invoices.add(invoice)

    bag.was_delivered = True
    bag.save()

    #TODO: remove the bag

    logger.info(f'Subscription was created with id {subscription.id}')
