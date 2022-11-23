import logging
from datetime import datetime, timedelta
from typing import Optional
from django.utils import timezone

from celery import Task, shared_task
from breathecode.authenticate.actions import get_user_settings

from breathecode.notify import actions as notify_actions
from breathecode.payments import actions
from breathecode.payments.services.stripe import Stripe
from dateutil.relativedelta import relativedelta

from .models import Bag, Consumable, Invoice, Subscription

logger = logging.getLogger(__name__)


class BaseTaskWithRetry(Task):
    autoretry_for = (Exception, )
    #                                           seconds
    retry_kwargs = {'max_retries': 5, 'countdown': 60 * 5}
    retry_backoff = True


@shared_task(bind=True, base=BaseTaskWithRetry)
def renew_consumables(self, subscription_id: int):
    """
    The purpose of this function is renew every service items belongs to a subscription.
    """

    logger.info(f'Starting renew_consumables for subscription {subscription_id}')

    if not (subscription := Subscription.objects.filter(id=subscription_id).first()):
        logger.error(f'Subscription with id {subscription_id} not found')
        return

    utc_now = timezone.now()
    if subscription.valid_until < utc_now:
        logger.error(f'This subscription needs to be paid to renew the consumables')
        return

    for scheduler in subscription.service_stock_schedulers.filter():
        unit = scheduler.service_item.renew_at
        unit_type = scheduler.service_item.renew_at_unit
        delta = actions.calculate_relative_delta(unit, unit_type)

        if scheduler.last_renew + delta - timedelta(hours=2) <= utc_now:
            scheduler.last_renew = scheduler.last_renew + delta
            scheduler.save()

            consumable = Consumable(service_item=scheduler.service_item,
                                    user=subscription.user,
                                    valid_until=scheduler.last_renew + delta,
                                    unit_type=scheduler.service_item.unit_type,
                                    how_many=scheduler.service_item.how_many)

            consumable.save()

            scheduler.consumables.add(consumable)


@shared_task(bind=True, base=BaseTaskWithRetry)
def renew_subscription(self, subscription_id: int, from_datetime: Optional[datetime] = None):
    """
    The purpose of this function is just to renew a subscription, not more than this.
    """

    logger.info(f'Starting renew_subscription for subscription {subscription_id}')

    if not (subscription := Subscription.objects.filter(id=subscription_id).first()):
        logger.error(f'Subscription with id {subscription_id} not found')
        return

    if not from_datetime:
        from_datetime = timezone.now()

    settings = get_user_settings(subscription.user.id)

    try:
        s = Stripe()
        s.set_language_from_settings(settings)
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

    subscription.paid_at = from_datetime
    subscription.valid_until = from_datetime + actions.calculate_relative_delta(
        subscription.pay_every_unit, subscription.pay_every_unit)

    subscription.invoices.add(invoice)

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

    renew_consumables.delay(subscription.id)


@shared_task(bind=True, base=BaseTaskWithRetry)
def build_service_stock_scheduler(self, subscription_id: int):
    logger.info(f'Starting build_service_stock_scheduler for subscription {subscription_id}')

    if not (subscription := Subscription.objects.filter(id=subscription_id).first()):
        logger.error(f'Subscription with id {subscription_id} not found')
        return

    schedulers = subscription.service_stock_schedulers.all()
    service_items = subscription.service_items.all()
    plans = subscription.plans.all()
    utc_now = timezone.now()

    not_found = [(x.service_item.service.id, x.service_item.service.how_many, x.is_belongs_to_plan)
                 for x in schedulers]

    for service_item in service_items:
        query = (service_item.service.id, service_item.service.how_many, False)
        if query in not_found:
            not_found.remove(query)
            continue

        subscription.service_stock_schedulers.create(service_item=service_item,
                                                     is_belongs_to_plan=False,
                                                     last_renew=utc_now)

    for plan in plans:
        for service_item in plan.service_items:
            query = (service_item.service.id, service_item.service.how_many, True)
            if query in not_found:
                not_found.remove(query)
                continue

            subscription.service_stock_schedulers.create(service_item=service_item,
                                                         is_belongs_to_plan=True,
                                                         last_renew=utc_now)

    for scheduler in schedulers:
        query = (scheduler.service_item.service.id, scheduler.service_item.service.how_many,
                 scheduler.is_belongs_to_plan)

        if query in not_found:
            scheduler.delete()

    renew_consumables.delay(subscription.id)


@shared_task(bind=True, base=BaseTaskWithRetry)
def build_subscription(self, bag_id: int, invoice_id: int):
    logger.info(f'Starting build_subscription for bag {bag_id}')

    if not (bag := Bag.objects.filter(id=bag_id, status='PAID', was_delivered=False).first()):
        logger.error(f'Bag with id {bag_id} not found')
        return

    if not (invoice := Invoice.objects.filter(id=invoice_id, status='FULFILLED').first()):
        logger.error(f'Invoice with id {invoice_id} not found')
        return

    months = 1

    if bag.chosen_period == 'QUARTER':
        months = 3

    elif bag.chosen_period == 'HALF':
        months = 6

    elif bag.chosen_period == 'YEAR':
        months = 12

    subscription = Subscription.objects.create(user=bag.user,
                                               paid_at=invoice.paid_at,
                                               valid_until=invoice.paid_at + relativedelta(months=months),
                                               status='ACTIVE')

    subscription.plans.set(bag.plans.all())
    subscription.service_items.set(bag.service_items.all())

    subscription.save()
    subscription.invoices.add(invoice)

    bag.was_delivered = True
    bag.save()

    #TODO: remove the bag

    build_service_stock_scheduler.delay(subscription.id)

    logger.info(f'Subscription was created with id {subscription.id}')
