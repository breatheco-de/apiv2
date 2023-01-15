import logging
from datetime import datetime, timedelta
import traceback
from typing import Optional
from django.utils import timezone

from celery import Task, shared_task
from breathecode.authenticate.actions import get_user_settings

from breathecode.notify import actions as notify_actions
from breathecode.payments import actions
from breathecode.payments.services.stripe import Stripe
from dateutil.relativedelta import relativedelta
from django.db.models import Q
from breathecode.payments.signals import consume_service

from .models import Bag, Consumable, ConsumptionSession, Invoice, PlanFinancing, PlanServiceItem, PlanServiceItemHandler, ServiceStockScheduler, Subscription, SubscriptionServiceItem

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

    for scheduler in ServiceStockScheduler.objects.filter(subscription=subscription):
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
        bag = actions.get_bag_from_subscription(subscription, settings)
    except Exception as e:
        logger.error(f'Error getting bag from subscription {subscription_id}: {e}')
        subscription.status = 'ERROR'
        subscription.status_message = str(e)
        subscription.save()
        return

    amount = actions.get_amount_by_chosen_period(bag, bag.chosen_period)

    try:
        s = Stripe()
        s.set_language_from_settings(settings)
        invoice = s.pay(subscription.user, bag, amount, currency=bag.currency)

    except Exception as e:
        notify_actions.send_email_message(
            'message',
            subscription.user.email,
            {
                'SUBJECT': 'Your 4Geeks subscription could not be renewed',
                'MESSAGE': f'Please update your payment methods',
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
def build_service_stock_scheduler_from_subscription(self,
                                                    subscription_id: int,
                                                    user_id: Optional[int] = None):
    logger.info(
        f'Starting build_service_stock_scheduler_from_subscription for subscription {subscription_id}')

    k = {
        'subscription': 'user__id',
        # service items of
        'handlers': {
            'of_subscription': 'subscription_handler__subscription__user__id',
            'of_plan': 'plan_handler__subscription__user__id',
        },
    }

    additional_args = {
        'subscription': {
            k['subscription']: user_id
        } if user_id else {},
        # service items of
        'handlers': {
            'of_subscription': {
                k['handlers']['of_subscription']: user_id,
            },
            'of_plan': {
                k['handlers']['of_plan']: user_id,
            },
        },
    }

    if not (subscription := Subscription.objects.filter(id=subscription_id, **
                                                        additional_args['subscription']).first()):
        logger.error(f'Subscription with id {subscription_id} not found')
        return

    service_items = SubscriptionServiceItem.objects.filter(subscription=subscription)
    plans = PlanServiceItemHandler.objects.filter(subscription=subscription)
    utc_now = timezone.now()

    for subscription_handler in service_items:
        ServiceStockScheduler.objects.get_or_create(subscription_handler=subscription_handler,
                                                    last_renew=utc_now)

    for plan_handler in plans:
        ServiceStockScheduler.objects.get_or_create(plan_handler=plan_handler, last_renew=utc_now)

    renew_consumables.delay(subscription.id)


@shared_task(bind=True, base=BaseTaskWithRetry)
def build_service_stock_scheduler_from_plan_financing(self,
                                                      plan_financing_id: int,
                                                      user_id: Optional[int] = None):
    logger.info(
        f'Starting build_service_stock_scheduler_from_plan_financing for subscription {plan_financing_id}')

    k = {
        'subscription': 'user__id',
        # service items of
        'handlers': {
            'of_subscription': 'subscription_handler__subscription__user__id',
            'of_plan': 'plan_handler__subscription__user__id',
        },
    }

    additional_args = {
        'subscription': {
            k['subscription']: user_id
        } if user_id else {},
        # service items of
        'handlers': {
            'of_subscription': {
                k['handlers']['of_subscription']: user_id,
            },
            'of_plan': {
                k['handlers']['of_plan']: user_id,
            },
        },
    }

    if not (plan_financing := PlanFinancing.objects.filter(id=plan_financing_id,
                                                           **additional_args['subscription']).first()):
        logger.error(f'PlanFinancing with id {plan_financing_id} not found')
        return

    plans = PlanServiceItem.objects.filter(plan_financing=plan_financing)
    utc_now = timezone.now()

    for plan_handler in plans:
        ServiceStockScheduler.objects.get_or_create(plan_handler=plan_handler, last_renew=utc_now)

    # renew_consumables.delay(subscription.id)


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
                                               academy=bag.academy,
                                               valid_until=None,
                                               next_payment_at=invoice.paid_at + relativedelta(months=months),
                                               status='ACTIVE')

    subscription.plans.set(bag.plans.all())
    subscription.service_items.set(bag.service_items.all())

    subscription.save()
    subscription.invoices.add(invoice)

    bag.was_delivered = True
    bag.save()

    build_service_stock_scheduler_from_subscription.delay(subscription.id)

    logger.info(f'Subscription was created with id {subscription.id}')


@shared_task(bind=True, base=BaseTaskWithRetry)
def build_plan_financing(self, bag_id: int, invoice_id: int):
    logger.info(f'Starting build_financing for bag {bag_id}')

    if not (bag := Bag.objects.filter(id=bag_id, status='PAID', was_delivered=False).first()):
        logger.error(f'Bag with id {bag_id} not found')
        return

    if not (invoice := Invoice.objects.filter(id=invoice_id, status='FULFILLED').first()):
        logger.error(f'Invoice with id {invoice_id} not found')
        return

    months = bag.how_many_installments

    financing = PlanFinancing.objects.create(user=bag.user,
                                             paid_at=invoice.paid_at,
                                             academy=bag.academy,
                                             paid_until=invoice.paid_at + relativedelta(months=months),
                                             status='ACTIVE')

    financing.plans.set(bag.plans.all())

    financing.save()
    financing.invoices.add(invoice)

    bag.was_delivered = True
    bag.save()

    build_service_stock_scheduler_from_plan_financing.delay(financing.id)

    logger.info(f'PlanFinancing was created with id {financing.id}')


@shared_task(bind=True, base=BaseTaskWithRetry)
def build_free_trial(self, bag_id: int, invoice_id: int):
    logger.info(f'Starting build_free_trial for bag {bag_id}')


@shared_task(bind=True, base=BaseTaskWithRetry)
# def async_consume(self, bag_id: int, eta: datetime):
def end_the_consumption_session(self, consumption_session_id: int, how_many: float = 1.0):
    logger.info(f'Starting end_the_consumption_session for ConsumptionSession {consumption_session_id}')

    session = ConsumptionSession.objects.filter(id=consumption_session_id).first()
    if not session:
        logger.error(f'ConsumptionSession with id {consumption_session_id} not found')
        return

    consumable = session.consumable
    consume_service.send(instance=consumable, sender=consumable.__class__, how_many=how_many)

    session.was_discounted = True
    session.status = 'DONE'
