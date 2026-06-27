import ast
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Optional
from urllib.parse import urlencode

from capyc.core.i18n import translation
from dateutil.relativedelta import relativedelta
from django.core.cache import cache
from django.db.models import F, Sum
from django.utils import timezone
from django_redis import get_redis_connection
from redis.exceptions import LockError
from task_manager.core.exceptions import AbortTask, RetryTask
from task_manager.django.actions import schedule_task
from task_manager.django.decorators import task

from breathecode.admissions.models import Cohort
from breathecode.authenticate.actions import get_app_url, get_user_settings
from breathecode.authenticate.models import AcademyAuthSettings
from breathecode.media.models import File
from breathecode.notify import actions as notify_actions
from breathecode.payments import actions
from breathecode.payments.services.stripe import Stripe
from breathecode.payments.signals import consume_service, reimburse_service_units
from breathecode.services.google.google import Google
from breathecode.utils.decorators import TaskPriority
from breathecode.utils.redis import Lock

from .models import (
    AbstractIOweYou,
    AcademyPaymentSettings,
    Bag,
    CohortSet,
    Consumable,
    ConsumptionSession,
    Coupon,
    CreditLedgerEntry,
    Invoice,
    PaymentMethod,
    Plan,
    PlanFinancing,
    PlanFinancingSeat,
    PlanFinancingTeam,
    PlanOffer,
    PlanServiceItem,
    PlanServiceItemHandler,
    ProofOfPayment,
    Service,
    ServiceStockScheduler,
    Subscription,
    SubscriptionBillingTeam,
    SubscriptionSeat,
    SubscriptionServiceItem,
)

logger = logging.getLogger(__name__)
IS_DJANGO_REDIS = hasattr(cache, "fake") is False


@task(bind=True, priority=TaskPriority.WEB_SERVICE_PAYMENT.value)
def renew_consumables(self, scheduler_id: int, **_: Any):
    """Renew consumables."""

    def get_resource_lookup(i_owe_you: AbstractIOweYou, service: Service):
        lookups = {}

        key = service.type.lower()
        value = getattr(i_owe_you, f"selected_{key}", None)
        if value:
            lookups[key] = value

        return lookups

    def get_extras(scheduler: ServiceStockScheduler):
        extras = {}
        if scheduler.subscription_seat:
            extras["subscription_seat_id"] = scheduler.subscription_seat.id
            extras["subscription_billing_team_id"] = scheduler.subscription_seat.billing_team.id

        if scheduler.subscription_billing_team:
            extras["user"] = None
            if (
                scheduler.subscription_billing_team.consumption_strategy
                == SubscriptionBillingTeam.ConsumptionStrategy.PER_TEAM
            ):
                extras["subscription_seat_id"] = None

            extras["subscription_billing_team_id"] = scheduler.subscription_billing_team.id

        if scheduler.plan_financing_seat:
            extras["plan_financing_seat_id"] = scheduler.plan_financing_seat.id
            extras["plan_financing_team_id"] = scheduler.plan_financing_seat.team_id

        if scheduler.plan_financing_team:
            extras["user"] = None
            extras["plan_financing_team_id"] = scheduler.plan_financing_team.id

        return extras

    logger.info(f"Starting renew_consumables for service stock scheduler {scheduler_id}")

    if not (scheduler := ServiceStockScheduler.objects.filter(id=scheduler_id).first()):
        raise RetryTask(f"ServiceStockScheduler with id {scheduler_id} not found")

    utc_now = timezone.now()
    extras = get_extras(scheduler)

    # is over
    if (
        scheduler.plan_handler
        and scheduler.plan_handler.subscription
        and scheduler.plan_handler.subscription.valid_until
        and scheduler.plan_handler.subscription.valid_until < utc_now
    ):
        raise AbortTask(f"The subscription {scheduler.plan_handler.subscription.id} is over")

    # it needs to be paid
    if (
        scheduler.plan_handler
        and scheduler.plan_handler.subscription
        and scheduler.plan_handler.subscription.next_payment_at < utc_now
    ):
        raise AbortTask(
            f"The subscription {scheduler.plan_handler.subscription.id} needs to be paid to renew the consumables"
        )

    # is over
    if (
        scheduler.plan_handler
        and scheduler.plan_handler.plan_financing
        and scheduler.plan_handler.plan_financing.plan_expires_at < utc_now
    ):
        raise AbortTask(f"The plan financing {scheduler.plan_handler.plan_financing.id} is over")

    if (
        scheduler.plan_handler
        and scheduler.plan_handler.plan_financing
        and scheduler.plan_handler.plan_financing.status == PlanFinancing.Status.ACTIVE
        and scheduler.plan_handler.plan_financing.next_payment_at < utc_now
    ):
        raise AbortTask(
            f"The plan financing {scheduler.plan_handler.plan_financing.id} needs to be paid to renew "
            "the consumables"
        )

    # is over
    if (
        scheduler.subscription_handler
        and scheduler.subscription_handler.subscription
        and scheduler.subscription_handler.subscription.valid_until
        and scheduler.subscription_handler.subscription.valid_until < utc_now
    ):
        raise AbortTask(f"The subscription {scheduler.subscription_handler.subscription.id} is over")

    # it needs to be paid
    if (
        scheduler.subscription_handler
        and scheduler.subscription_handler.subscription
        and scheduler.subscription_handler.subscription.next_payment_at < utc_now
    ):
        raise AbortTask(
            f"The subscription {scheduler.subscription_handler.subscription.id} needs to be paid to renew "
            "the consumables"
        )

    service_item = None
    resource_valid_until = None
    resource_next_payment_at = None
    selected_lookup = {}
    subscription = None
    plan_financing = None

    if scheduler.plan_handler and scheduler.plan_handler.subscription:
        user = scheduler.plan_handler.subscription.user
        service_item = scheduler.plan_handler.handler.service_item
        resource_valid_until = scheduler.plan_handler.subscription.valid_until
        resource_next_payment_at = scheduler.plan_handler.subscription.next_payment_at
        subscription = scheduler.plan_handler.subscription

        selected_lookup = get_resource_lookup(scheduler.plan_handler.subscription, service_item.service)

    elif scheduler.plan_handler and scheduler.plan_handler.plan_financing:
        user = scheduler.plan_handler.plan_financing.user
        service_item = scheduler.plan_handler.handler.service_item
        resource_valid_until = scheduler.plan_handler.plan_financing.plan_expires_at
        resource_next_payment_at = scheduler.plan_handler.plan_financing.next_payment_at
        plan_financing = scheduler.plan_handler.plan_financing

        selected_lookup = get_resource_lookup(scheduler.plan_handler.plan_financing, service_item.service)

    elif scheduler.subscription_handler and scheduler.subscription_handler.subscription:
        user = scheduler.subscription_handler.subscription.user
        service_item = scheduler.subscription_handler.service_item
        resource_valid_until = scheduler.subscription_handler.subscription.valid_until
        resource_next_payment_at = scheduler.subscription_handler.subscription.next_payment_at
        subscription = scheduler.subscription_handler.subscription

        selected_lookup = get_resource_lookup(scheduler.subscription_handler.subscription, service_item.service)

    # If resource is Subscription and this scheduler is tied to a subscription seat,
    # issue the consumable for the seat assignee (or None if not yet assigned) instead of the subscription owner.
    if subscription and scheduler.subscription_seat:
        # Use the seat's user if assigned, otherwise None (waiting for invitation acceptance)
        user = scheduler.subscription_seat.user if scheduler.subscription_seat.user_id else None

    if plan_financing and scheduler.plan_financing_seat:
        user = scheduler.plan_financing_seat.user if scheduler.plan_financing_seat.user_id else None

    if plan_financing and scheduler.plan_financing_team:
        user = None

    unit = service_item.renew_at
    unit_type = service_item.renew_at_unit

    delta = actions.calculate_relative_delta(unit, unit_type)
    scheduler.valid_until = scheduler.valid_until or utc_now

    max_attempts = 100
    attempts = 0

    while attempts < max_attempts:
        new_valid_until = scheduler.valid_until + delta

        if new_valid_until > utc_now:
            if attempts > 0:
                logger.info(f"Scheduler {scheduler.id}: Found future date after {attempts + 1} attempts")
            scheduler.valid_until = new_valid_until
            break

        scheduler.valid_until = new_valid_until
        attempts += 1

        if attempts >= max_attempts:
            logger.warning(f"Could not find a future date for scheduler {scheduler.id} after {max_attempts} attempts")
            scheduler.valid_until = scheduler.valid_until + delta
            break

    if resource_valid_until and scheduler.valid_until and scheduler.valid_until > resource_valid_until:
        scheduler.valid_until = resource_valid_until

    if (
        not resource_valid_until
        and resource_next_payment_at
        and scheduler.valid_until
        and scheduler.valid_until > resource_next_payment_at
    ):
        scheduler.valid_until = resource_next_payment_at

    scheduler.save()

    if not selected_lookup and service_item.service.type != "VOID":
        logger.error(f"The Plan not have a resource linked to it for the ServiceStockScheduler {scheduler.id}")
        return

    if "user" not in extras:
        extras["user"] = user

    if scheduler.consumables.filter(valid_until=scheduler.valid_until).exists():
        raise AbortTask(
            f"Consumable with valid_until {scheduler.valid_until} already exists for scheduler {scheduler.id}, skipping to avoid duplicate"
        )

    consumable = Consumable(
        service_item=service_item,
        unit_type=service_item.unit_type,
        how_many=service_item.how_many,
        valid_until=scheduler.valid_until,
        subscription=subscription,
        plan_financing=plan_financing,
        **selected_lookup,
        **extras,
    )

    consumable.save()

    scheduler.consumables.add(consumable)

    if service_item.service.consumer == Service.Consumer.VPS_SERVER and service_item.how_many > 0:
        actions.align_consumer_vps_stock_with_active_machines(consumable)

    if selected_lookup:

        key = list(selected_lookup.keys())[0]
        id = selected_lookup[key].id
        name = key.replace("selected_", "").replace("_", " ")
        logger.info(f"The consumable {consumable.id} for {name} {id} was built")

    else:
        logger.info(f"The consumable {consumable.id} was built")

    logger.info(f"The scheduler {scheduler.id} was renewed")


@task(bind=True, priority=TaskPriority.WEB_SERVICE_PAYMENT.value)
def renew_subscription_consumables(
    self,
    subscription_id: int,
    seat_id: Optional[int] = None,
    service_ids: Optional[list[int]] = None,
    **_: Any,
):
    """Renew consumables belongs to a subscription."""

    logger.info(f"Starting renew_subscription_consumables for id {subscription_id}")

    if not (subscription := Subscription.objects.filter(id=subscription_id).first()):
        raise RetryTask(f"Subscription with id {subscription_id} not found")

    if subscription.status in [
        Subscription.Status.DEPRECATED,
        Subscription.Status.EXPIRED,
        Subscription.Status.PAYMENT_ISSUE,
    ]:
        raise AbortTask(f"The subscription {subscription.id} is deprecated, expired or has a payment issue")

    # Check if subscription has deleted or discontinued plans
    if subscription.plans.filter(status__in=[Plan.Status.DISCONTINUED, Plan.Status.DELETED]).exists():
        subscription.status = Subscription.Status.DEPRECATED
        subscription.save()
        raise AbortTask(
            f"The subscription {subscription.id} has deleted/discontinued plans, "
            "marked as deprecated, consumables will not be renewed"
        )

    subscription_seat = None
    if seat_id and not (
        subscription_seat := SubscriptionSeat.objects.filter(
            billing_team__subscription=subscription, id=seat_id
        ).first()
    ):
        raise RetryTask(f"SubscriptionSeat with id {seat_id} not found")

    utc_now = timezone.now()
    if subscription.valid_until and subscription.valid_until < utc_now:
        raise AbortTask(f"The subscription {subscription.id} is over")

    if subscription.next_payment_at < utc_now:
        raise AbortTask(f"The subscription {subscription.id} needs to be paid to renew the consumables")

    subscription_schedulers = ServiceStockScheduler.objects.filter(
        subscription_handler__subscription=subscription, subscription_seat=subscription_seat
    )
    if service_ids:
        subscription_schedulers = subscription_schedulers.filter(
            subscription_handler__service_item__service_id__in=service_ids
        )

    for scheduler in subscription_schedulers:
        renew_consumables.delay(scheduler.id)

    plan_schedulers = ServiceStockScheduler.objects.filter(
        plan_handler__subscription=subscription, subscription_seat=subscription_seat
    )
    if service_ids:
        plan_schedulers = plan_schedulers.filter(plan_handler__handler__service_item__service_id__in=service_ids)

    for scheduler in plan_schedulers:
        renew_consumables.delay(scheduler.id)


@task(bind=True, priority=TaskPriority.WEB_SERVICE_PAYMENT.value)
def renew_plan_financing_consumables(
    self,
    plan_financing_id: int,
    seat_id: Optional[int] = None,
    service_ids: Optional[list[int]] = None,
    **_: Any,
):
    """Renew consumables belongs to a plan financing."""

    logger.info(f"Starting renew_plan_financing_consumables for id {plan_financing_id}")

    if not (plan_financing := PlanFinancing.objects.filter(id=plan_financing_id).first()):
        raise RetryTask(f"PlanFinancing with id {plan_financing_id} not found")

    if plan_financing.status in [
        PlanFinancing.Status.CANCELLED,
        PlanFinancing.Status.DEPRECATED,
        PlanFinancing.Status.EXPIRED,
    ]:
        raise AbortTask(f"The plan financing {plan_financing.id} is cancelled, deprecated or expired")

    # A discontinued catalog plan must not invalidate an already-signed financing contract.
    # Deleted plans stop consumable renewals, but financing status must not be forced to DEPRECATED
    # because the model explicitly forbids that status.
    if plan_financing.plans.filter(status=Plan.Status.DELETED).exists():
        raise AbortTask(f"The plan financing {plan_financing.id} has deleted plans, " "consumables will not be renewed")

    utc_now = timezone.now()
    if plan_financing.next_payment_at < utc_now and plan_financing.status != PlanFinancing.Status.FULLY_PAID:
        raise AbortTask(f"The PlanFinancing {plan_financing.id} needs to be paid to renew the consumables")

    if plan_financing.plan_expires_at and plan_financing.plan_expires_at < utc_now:
        logger.info(f"The services related to PlanFinancing {plan_financing.id} is over")
        return

    scheduler_filters = {"plan_handler__plan_financing": plan_financing}

    if seat_id is not None:
        if not PlanFinancingSeat.objects.filter(
            id=seat_id,
            team__financing=plan_financing,
        ).exists():
            raise RetryTask(f"PlanFinancingSeat with id {seat_id} not found")

        scheduler_filters["plan_financing_seat_id"] = seat_id

    if service_ids:
        scheduler_filters["plan_handler__handler__service_item__service_id__in"] = service_ids

    schedulers = ServiceStockScheduler.objects.filter(**scheduler_filters)

    if seat_id is not None and not schedulers.exists():
        logger.info(
            "No schedulers found for seat %s in plan financing %s, skipping consumable renewal",
            seat_id,
            plan_financing.id,
        )
        return

    for scheduler in schedulers:
        renew_consumables.delay(scheduler.id)


@task(bind=True, priority=TaskPriority.NOTIFICATION.value)
def notify_subscription_renewal(self, subscription_id: int, **_: Any):
    """
    Notify user before subscription renewal with an early payment link.
    """

    if not (subscription := Subscription.objects.filter(id=subscription_id).first()):
        raise AbortTask(f"Subscription {subscription_id} not found")

    no_charge_statuses = [
        Subscription.Status.CANCELLED,
        Subscription.Status.DEPRECATED,
        Subscription.Status.EXPIRED,
    ]

    if subscription.status in no_charge_statuses:
        raise AbortTask(f"Subscription {subscription_id} is {subscription.status}, skipping notification")

    utc_now = timezone.now()

    if subscription.next_payment_at > utc_now:

        period_timedelta = actions.calculate_relative_delta(subscription.pay_every, subscription.pay_every_unit)
        cycle_start = (subscription.next_payment_at - period_timedelta) + timedelta(days=1)

        recent_payment = (
            subscription.invoices.filter(
                status="FULFILLED",
                paid_at__gte=cycle_start,
                paid_at__lte=subscription.next_payment_at,
            )
            .order_by("-paid_at")
            .first()
        )

        if recent_payment:
            raise AbortTask(f"Subscription {subscription_id} already renewed for current cycle")

    settings = get_user_settings(subscription.user.id)

    payment_settings = AcademyPaymentSettings.objects.filter(academy=subscription.academy).first()
    early_renewal_window_days = payment_settings.early_renewal_window_days if payment_settings else 0

    if early_renewal_window_days == 0:
        raise AbortTask(f"Early renewal not allowed for academy with id {subscription.academy.id}")

    if utc_now > subscription.next_payment_at:
        raise AbortTask(f"Subscription {subscription_id} renewal already passed")

    if utc_now < subscription.next_payment_at - timedelta(days=early_renewal_window_days):
        raise AbortTask(f"Subscription {subscription_id} renewal is scheduled too early")

    plan = subscription.plans.first()
    plan_title = plan.title or plan.slug if plan else "plan"

    renewal_date = subscription.next_payment_at.strftime("%B %d, %Y")
    params = {
        "plan": plan.slug if plan else "",
        "subscription_id": subscription.id,
    }

    days_until_renewal = (subscription.next_payment_at - utc_now).days
    subject = translation(
        settings.lang,
        en=f"Your {plan_title} subscription renews in {days_until_renewal} days",
        es=f"Tu suscripción {plan_title} se renueva en {days_until_renewal} días",
    )

    message = translation(
        settings.lang,
        en=f"Your {plan_title} subscription will renew on {renewal_date}. If you have a credit card registered, it will be used automatically, or you can pay in advance with another method:",
        es=f"Tu suscripción {plan_title} se renovará el {renewal_date}. Si tienes una tarjeta de crédito registrada, se utilizará automáticamente, o puedes pagar por adelantado con otro método:",
    )

    button = translation(settings.lang, en="Pay Now", es="Pagar Ahora")

    notify_actions.send_email_message(
        "message",
        subscription.user.email,
        {
            "SUBJECT": subject,
            "MESSAGE": message,
            "BUTTON": button,
            "LINK": f"{get_app_url()}/renew?{urlencode(params)}",
        },
        academy=subscription.academy,
    )

    logger.info(f"Sent renewal notification for subscription {subscription_id}")


def fallback_charge_subscription(self, subscription_id: int, exception: Exception, **_: Any):
    if not (subscription := Subscription.objects.filter(id=subscription_id).first()):
        return

    settings = get_user_settings(subscription.user.id)
    utc_now = timezone.now()

    message = f"charge_subscription is failing for the subscription {subscription.id}: "
    message += str(exception)[: 250 - len(message)]

    subscription.status = "ERROR"
    subscription.status_message = message
    subscription.save()

    invoice = subscription.invoices.filter(paid_at__gte=utc_now - timedelta(days=1)).order_by("-id").first()

    if invoice:
        coinbase_method = PaymentMethod.objects.filter(is_crypto=True).first()
        if invoice.payment_method != coinbase_method and not invoice.coinbase_charge_id:
            s = Stripe(academy=subscription.academy)
            s.set_language(settings.lang)
            s.refund_payment(invoice)


@task(
    bind=True, transaction=True, fallback=fallback_charge_subscription, priority=TaskPriority.WEB_SERVICE_PAYMENT.value
)
def charge_subscription(self, subscription_id: int, **_: Any):
    """Renews a subscription."""

    logger.info(f"Starting charge_subscription for subscription {subscription_id}")

    def alert_payment_issue(message: str, button: str) -> None:
        plan = subscription.plans.first()
        plan_title = plan.title or plan.slug if plan else "plan"

        subject = translation(
            settings.lang,
            en=f"Your {plan_title} subscription could not be renewed",
            es=f"Tu suscripción {plan_title} no pudo ser renovada",
        )

        params = {"plan": plan.slug if plan else "", "subscription_id": subscription.id}

        notify_actions.send_email_message(
            "message",
            subscription.user.email,
            {
                "SUBJECT": subject,
                "MESSAGE": message,
                "BUTTON": button,
                "LINK": f"{get_app_url()}/renew?{urlencode(params)}",
            },
            academy=subscription.academy,
        )

        if bag:
            bag.delete()

        if subscription.status not in [
            Subscription.Status.CANCELLED,
            Subscription.Status.DEPRECATED,
            Subscription.Status.EXPIRED,
        ]:
            subscription.status = "PAYMENT_ISSUE"
            subscription.save()

    def handle_deprecated_subscription():
        plan = subscription.plans.first()
        link = None

        if plan and (offer := PlanOffer.objects.filter(original_plan=plan).first()):
            link = f"{get_app_url()}/checkout?plan={offer.suggested_plan.slug}"

        elif plan is None:
            raise AbortTask(f"Deprecated subscription with id {subscription.id} has no plan")

        subject = translation(
            settings.lang,
            en=f"Your 4Geeks subscription to {plan.slug} has been discontinued",
            es=f"Tu suscripción 4Geeks a {plan.slug} ha sido descontinuada",
        )

        obj = {
            "SUBJECT": subject,
        }

        if link:
            button = translation(
                settings.lang,
                en="See suggested plan",
                es="Ver plan sugerido",
            )
            obj["LINK"] = link
            obj["BUTTON"] = button

            message = translation(
                settings.lang,
                en=f"We regret to inform you that your 4Geeks subscription to {plan.slug} has been discontinued. Please check our suggested plans for alternatives.",
                es=f"Lamentamos informarte que tu suscripción 4Geeks a {plan.slug} ha sido descontinuada. Por favor, revisa nuestros planes sugeridos para alternativas.",
            )

        else:
            message = translation(
                settings.lang,
                en=f"We regret to inform you that your 4Geeks subscription to {plan.slug} has been discontinued.",
                es=f"Lamentamos informarte que tu suscripción 4Geeks a {plan.slug} ha sido descontinuada.",
            )

        obj["MESSAGE"] = message

        notify_actions.send_email_message(
            "message",
            subscription.user.email,
            obj,
            academy=subscription.academy,
        )
        raise AbortTask(f"Subscription with id {subscription.id} is deprecated")

    bag = None
    client = None
    if IS_DJANGO_REDIS:
        client = get_redis_connection("default")

    statuses = [
        Subscription.Status.ERROR,
        Subscription.Status.ACTIVE,
        Subscription.Status.PAYMENT_ISSUE,
        Subscription.Status.FULLY_PAID,
    ]

    no_charge_statuses = [
        Subscription.Status.DEPRECATED,
        Subscription.Status.EXPIRED,
    ]

    try:
        with Lock(client, f"lock:subscription:{subscription_id}", timeout=30, blocking_timeout=30):
            if not (subscription := Subscription.objects.filter(id=subscription_id).first()):
                raise AbortTask(f"Subscription with id {subscription_id} not found")

            utc_now = timezone.now()

            if subscription.status == Subscription.Status.CANCELLED:
                if subscription.next_payment_at and subscription.next_payment_at <= utc_now:
                    from breathecode.payments import signals

                    signals.revoke_plan_permissions.send_robust(instance=subscription, sender=Subscription)
                raise AbortTask(
                    f"Subscription with id {subscription_id} is in status {subscription.status} and cannot be charged"
                )

            if subscription.status in no_charge_statuses:
                raise AbortTask(
                    f"Subscription with id {subscription_id} is in status {subscription.status} and cannot be charged"
                )

            if subscription.status == Subscription.Status.PAYMENT_ISSUE:
                days_overdue = (utc_now - subscription.next_payment_at).days
                if days_overdue >= 5:
                    logger.warning(
                        f"charge_subscription: Subscription {subscription_id} cancelled after 5 days of payment failure"
                    )
                    subscription.status = Subscription.Status.EXPIRED
                    subscription.status_message = "Payment failed for more than 5 days"
                    subscription.save()
                    raise AbortTask(f"Subscription {subscription_id} cancelled after 5 days of payment failure")

            settings = get_user_settings(subscription.user.id)

            payment_settings = AcademyPaymentSettings.objects.filter(academy=subscription.academy).first()
            early_renewal_window_days = payment_settings.early_renewal_window_days if payment_settings else 2
            if early_renewal_window_days == 0:
                cooldown_days = 5
            else:
                cooldown_days = early_renewal_window_days

            if subscription.status == Subscription.Status.DEPRECATED:
                handle_deprecated_subscription()

            elif subscription.plans.filter(status__in=[Plan.Status.DISCONTINUED, Plan.Status.DELETED]).exists():
                subscription.status = Subscription.Status.DEPRECATED
                subscription.save()
                handle_deprecated_subscription()

            if subscription.valid_until and subscription.valid_until < utc_now and subscription.status in statuses:
                if subscription.status != Subscription.Status.EXPIRED:
                    subscription.status = Subscription.Status.EXPIRED
                    subscription.save()
                raise AbortTask(f"The subscription {subscription.id} is over")

            if subscription.next_payment_at > utc_now:
                raise AbortTask(f"The subscription with id {subscription_id} was paid this month")

            last_invoice = (
                subscription.invoices.filter(status=Invoice.Status.FULFILLED, bag__was_delivered=True)
                .order_by("-paid_at")
                .first()
            )

            if last_invoice and utc_now - last_invoice.paid_at < timedelta(days=cooldown_days):
                raise AbortTask(f"Subscription with id {subscription_id} was paid earlier")

            invoice = (
                subscription.invoices.filter(
                    paid_at__lte=utc_now, bag__was_delivered=False, status=Invoice.Status.FULFILLED
                )
                .order_by("-paid_at")
                .first()
            )

            if invoice:
                logger.info(
                    f"charge_subscription: Found existing payment for subscription {subscription_id}, "
                    f"invoice {invoice.id}, paid_at {invoice.paid_at}"
                )
                bag = invoice.bag

            else:
                if subscription.externally_managed:
                    message = translation(
                        settings.lang,
                        en="Please make your payment in your academy or use another payment method",
                        es="Por favor realiza tu pago en tu academia o utiliza otro método de pago",
                    )

                    button = translation(
                        settings.lang,
                        en="Renew with another method",
                        es="Renovar con otro método",
                    )
                    alert_payment_issue(message, button)

                    if subscription.status not in no_charge_statuses:
                        manager = schedule_task(charge_subscription, "1d")
                        if not manager.exists(subscription.id):
                            manager.call(subscription.id)

                    raise AbortTask(f"Payment to Subscription {subscription_id} failed")

                else:
                    try:
                        bag = actions.get_bag_from_subscription(subscription, settings)
                    except Exception as e:
                        logger.error(f"charge_subscription: Error getting bag from subscription {subscription_id}: {e}")
                        subscription.status = "ERROR"
                        subscription.status_message = str(e)
                        subscription.save()

                        if subscription.status not in no_charge_statuses:
                            manager = schedule_task(charge_subscription, "1d")
                            if not manager.exists(subscription.id):
                                manager.call(subscription.id)

                        raise AbortTask(f"Error getting bag from subscription {subscription_id}: {e}")

                    amount = actions.get_amount_by_chosen_period(bag, bag.chosen_period, settings.lang)

                    # Apply coupon discounts if they exist on the subscription or they are restricted to the user (only non-expired and with offers left)
                    utc_now = timezone.now()
                    coupons = bag.coupons.all()

                    if coupons:
                        amount = actions.get_discounted_price(amount, coupons)
                    try:
                        s = Stripe(academy=subscription.academy)
                        s.set_language(settings.lang)
                        team = SubscriptionBillingTeam.objects.filter(subscription=subscription).first()
                        invoice = s.pay(
                            subscription.user, bag, amount, currency=bag.currency, subscription_billing_team=team
                        )
                        invoice.amount_breakdown = actions.calculate_invoice_breakdown(
                            bag, invoice, settings.lang, chosen_period=bag.chosen_period
                        )
                        invoice.save(update_fields=["amount_breakdown"])

                    except Exception:
                        message = translation(
                            settings.lang,
                            en="Your payment with credit card was declined, please update your card or use another payment method",
                            es="Tu pago con tarjeta de crédito fue rechazado, por favor update tu tarjeta o utiliza otro método de pago",
                        )

                        button = translation(
                            settings.lang,
                            en="Change payment method",
                            es="Cambiar método de pago",
                        )
                        alert_payment_issue(message, button)

                        if subscription.status not in no_charge_statuses:
                            manager = schedule_task(charge_subscription, "1d")
                            if not manager.exists(subscription.id):
                                manager.call(subscription.id)

                        raise AbortTask(f"Payment to Subscription {subscription_id} failed")

            subscription.paid_at = utc_now
            delta = actions.calculate_relative_delta(subscription.pay_every, subscription.pay_every_unit)

            subscription.next_payment_at += delta
            while utc_now >= subscription.next_payment_at:
                subscription.next_payment_at += delta
                if subscription.valid_until:
                    subscription.valid_until += delta

            if subscription.valid_until and subscription.next_payment_at > subscription.valid_until:
                subscription.next_payment_at = subscription.valid_until

            subscription.invoices.add(invoice)
            subscription.status = "ACTIVE"
            subscription.status_message = None
            subscription.save()

            value = invoice.currency.format_price(invoice.amount)

            subject = translation(
                settings.lang,
                en="Your 4Geeks subscription was successfully renewed",
                es="Tu suscripción 4Geeks fue renovada exitosamente",
            )

            message = translation(settings.lang, en=f"The amount was {value}", es=f"El monto fue {value}")

            button = translation(settings.lang, en="See the invoice", es="Ver la factura")

            notify_actions.send_email_message(
                "message",
                invoice.user.email,
                {
                    "SUBJECT": subject,
                    "MESSAGE": message,
                    "BUTTON": button,
                    "LINK": f"{get_app_url()}/subscription/{subscription.id}",
                },
                academy=subscription.academy,
            )

            bag.was_delivered = True
            bag.save()

            if subscription.seat_service_item and subscription.seat_service_item.how_many > 0:
                team = SubscriptionBillingTeam.objects.filter(
                    subscription=subscription, defaults={"name": f"Team {subscription.id}"}
                ).first()
                if not team:
                    raise RetryTask(f"SubscriptionBillingTeam with id {subscription_id} not found")

                for seat in SubscriptionSeat.objects.filter(billing_team=team):
                    renew_subscription_consumables.delay(subscription.id, seat_id=seat.id)

                return

            renew_subscription_consumables.delay(subscription.id)

            # Schedule next charge based on days until next_payment_at
            days_until_next_payment = (subscription.next_payment_at - utc_now).days
            manager = schedule_task(charge_subscription, f"{days_until_next_payment}d")
            if not manager.exists(subscription.id):
                manager.call(subscription.id)

            if early_renewal_window_days > 0 and days_until_next_payment > early_renewal_window_days:
                notification_day = days_until_next_payment - early_renewal_window_days
                manager = schedule_task(notify_subscription_renewal, f"{notification_day}d")
                if not manager.exists(subscription.id):
                    manager.call(subscription.id)

    except LockError:
        raise RetryTask("Could not acquire lock for activity, operation timed out.")


@task(bind=True, priority=TaskPriority.NOTIFICATION.value)
def notify_plan_financing_renewal(self, plan_financing_id: int, **_: Any):
    "Notify user before plan financing installment with payment link."

    if not (plan_financing := PlanFinancing.objects.filter(id=plan_financing_id).first()):
        raise AbortTask(f"PlanFinancing {plan_financing_id} not found")

    no_charge_statuses = [
        PlanFinancing.Status.CANCELLED,
        PlanFinancing.Status.DEPRECATED,
        PlanFinancing.Status.EXPIRED,
        PlanFinancing.Status.FULLY_PAID,
    ]

    if plan_financing.status in no_charge_statuses:
        raise AbortTask(f"PlanFinancing {plan_financing_id} is {plan_financing.status}, skipping notification")

    utc_now = timezone.now()

    if plan_financing.next_payment_at > utc_now:
        period_timedelta = relativedelta(months=1)
        cycle_start = (plan_financing.next_payment_at - period_timedelta) + timedelta(days=1)

        recent_payment = (
            plan_financing.invoices.filter(
                status="FULFILLED",
                paid_at__gte=cycle_start,
                paid_at__lte=plan_financing.next_payment_at,
            )
            .order_by("-paid_at")
            .first()
        )

        if recent_payment:
            raise AbortTask(f"PlanFinancing {plan_financing_id} already renewed for current cycle")

    if (
        plan_financing.plan_expires_at
        and plan_financing.plan_expires_at < utc_now
        and plan_financing.valid_until
        and plan_financing.valid_until < utc_now
    ):
        raise AbortTask(f"PlanFinancing {plan_financing_id} has expired")

    payment_settings = AcademyPaymentSettings.objects.filter(academy=plan_financing.academy).first()
    early_renewal_window_days = payment_settings.early_renewal_window_days if payment_settings else 0

    if early_renewal_window_days == 0:
        raise AbortTask(f"Early renewal not allowed for academy with id {plan_financing.academy.id}")

    if utc_now > plan_financing.next_payment_at:
        raise AbortTask(f"PlanFinancing {plan_financing_id} renewal already passed")

    if utc_now < plan_financing.next_payment_at - timedelta(days=early_renewal_window_days):
        raise AbortTask(f"PlanFinancing {plan_financing_id} renewal is scheduled too early")

    settings = get_user_settings(plan_financing.user.id)

    invoices = plan_financing.invoices.order_by("created_at")
    first_invoice = invoices.first()

    if first_invoice is None:
        raise AbortTask(f"No invoices found for PlanFinancing {plan_financing_id}")

    paid_installments = plan_financing.invoices.filter(status="FULFILLED", bag__was_delivered=True).count()

    if paid_installments == plan_financing.how_many_installments:
        raise AbortTask(f"PlanFinancing {plan_financing_id} is fully paid")

    next_installment = paid_installments + 1

    plan = plan_financing.plans.first()
    plan_title = plan.title or plan.slug if plan else "plan"

    renewal_date = plan_financing.next_payment_at.strftime("%B %d, %Y")

    days_until_renewal = (plan_financing.next_payment_at - utc_now).days

    subject = translation(
        settings.lang,
        en=f"Your {plan_title} installment payment is due in {days_until_renewal} days",
        es=f"El pago de cuota de {plan_title} vence en {days_until_renewal} días",
    )

    message = translation(
        settings.lang,
        en=f"On {renewal_date}, you need to pay installment {next_installment} of {plan_title}. If you have a credit card registered, "
        "it will be used automatically, or you can pay in advance with another method",
        es=f"El {renewal_date} debes realizar el pago de la cuota {next_installment} de {plan_title}. Si tienes una tarjeta de crédito registrada, "
        "se utilizará automáticamente, o puedes pagar por adelantado con otro método:",
    )

    button = translation(settings.lang, en="Pay Now", es="Pagar Ahora")

    params = {
        "plan": plan.slug if plan else "",
        "plan_financing_id": plan_financing.id,
    }

    notify_actions.send_email_message(
        "message",
        plan_financing.user.email,
        {
            "SUBJECT": subject,
            "MESSAGE": message,
            "BUTTON": button,
            "LINK": f"{get_app_url()}/renew?{urlencode(params)}",
        },
        academy=plan_financing.academy,
    )

    logger.info(f"Sent installment notification for plan_financing {plan_financing_id}")


def fallback_charge_plan_financing(self, plan_financing_id: int, exception: Exception, **_: Any):
    if not (plan_financing := PlanFinancing.objects.filter(id=plan_financing_id).first()):
        return

    settings = get_user_settings(plan_financing.user.id)
    utc_now = timezone.now()

    message = f"charge_plan_financing is failing for the plan financing {plan_financing.id}: "
    message += str(exception)[: 250 - len(message)]

    plan_financing.status = "ERROR"
    plan_financing.status_message = message
    plan_financing.save()

    invoice = plan_financing.invoices.filter(paid_at__gte=utc_now - timedelta(days=1)).order_by("-id").first()

    if invoice:
        coinbase_method = PaymentMethod.objects.filter(is_crypto=True).first()
        if invoice.payment_method != coinbase_method and not invoice.coinbase_charge_id:
            s = Stripe(academy=plan_financing.academy)
            s.set_language(settings.lang)
            s.refund_payment(invoice)


@task(
    bind=True,
    transaction=True,
    fallback=fallback_charge_plan_financing,
    priority=TaskPriority.WEB_SERVICE_PAYMENT.value,
)
def charge_plan_financing(self, plan_financing_id: int, **_: Any):
    """Renew a plan financing."""

    logger.info(f"Starting charge_plan_financing for id {plan_financing_id}")

    def alert_payment_issue(message: str, button: str) -> None:
        plan = plan_financing.plans.first()
        plan_title = plan.title or plan.slug if plan else "plan"

        subject = translation(
            settings.lang,
            en=f"Your {plan_title} payment could not be processed",
            es=f"No pudimos procesar el pago de {plan_title}",
        )

        params = {"plan": plan.slug if plan else "", "plan_financing_id": plan_financing.id}

        notify_actions.send_email_message(
            "message",
            plan_financing.user.email,
            {
                "SUBJECT": subject,
                "MESSAGE": message,
                "BUTTON": button,
                "LINK": f"{get_app_url()}/renew?{urlencode(params)}",
            },
            academy=plan_financing.academy,
        )

        if bag:
            bag.delete()

        if plan_financing.status not in [
            PlanFinancing.Status.CANCELLED,
            PlanFinancing.Status.DEPRECATED,
            PlanFinancing.Status.EXPIRED,
        ]:
            plan_financing.status = "PAYMENT_ISSUE"
            plan_financing.save()

    bag = None
    client = None
    if IS_DJANGO_REDIS:
        client = get_redis_connection("default")

    statuses = [
        PlanFinancing.Status.ERROR,
        PlanFinancing.Status.ACTIVE,
        PlanFinancing.Status.PAYMENT_ISSUE,
        PlanFinancing.Status.FULLY_PAID,
    ]

    no_charge_statuses = [
        PlanFinancing.Status.DEPRECATED,
        PlanFinancing.Status.EXPIRED,
    ]

    try:
        with Lock(client, f"lock:plan_financing:{plan_financing_id}", timeout=30, blocking_timeout=30):

            if not (plan_financing := PlanFinancing.objects.filter(id=plan_financing_id).first()):
                raise AbortTask(f"PlanFinancing with id {plan_financing_id} not found")

            utc_now = timezone.now()

            if plan_financing.status == PlanFinancing.Status.CANCELLED:
                if plan_financing.next_payment_at and plan_financing.next_payment_at <= utc_now:
                    from breathecode.payments import signals

                    signals.revoke_plan_permissions.send_robust(instance=plan_financing, sender=PlanFinancing)
                raise AbortTask(
                    f"PlanFinancing with id {plan_financing_id} is in status {plan_financing.status} and cannot be charged"
                )

            if plan_financing.status in no_charge_statuses:
                raise AbortTask(
                    f"PlanFinancing with id {plan_financing_id} is in status {plan_financing.status} and cannot be charged"
                )

            if plan_financing.status == PlanFinancing.Status.PAYMENT_ISSUE:
                if (utc_now - plan_financing.next_payment_at).days >= 5:
                    plan_financing.status = PlanFinancing.Status.EXPIRED
                    plan_financing.status_message = "Payment failed for more than 5 days"
                    plan_financing.save()
                    raise AbortTask(f"PlanFinancing {plan_financing_id} cancelled after 5 days of payment failure")

            if plan_financing.status in statuses and (
                plan_financing.plan_expires_at < utc_now and plan_financing.valid_until < utc_now
            ):
                plan_financing.status = PlanFinancing.Status.EXPIRED
                plan_financing.status_message = "Plan financing has reached its expiration date"
                plan_financing.save()
                raise AbortTask(f"PlanFinancing with id {plan_financing_id} is over")

            if plan_financing.next_payment_at > utc_now:
                raise AbortTask(f"PlanFinancing with id {plan_financing_id} was paid this month")

            settings = get_user_settings(plan_financing.user.id)

            payment_settings = AcademyPaymentSettings.objects.filter(academy=plan_financing.academy).first()
            early_renewal_window_days = payment_settings.early_renewal_window_days if payment_settings else 2

            # Inform about discontinued catalog plans without stopping contractual financing charges.
            if plan_financing.plans.filter(status=Plan.Status.DISCONTINUED).exists():
                notification_cache_key = f"plan-financing-discontinued-notified:{plan_financing.id}"
                if not cache.get(notification_cache_key):
                    plan = plan_financing.plans.first()
                    link = None

                    if plan and (offer := PlanOffer.objects.filter(original_plan=plan).first()):
                        link = f"{get_app_url()}/checkout?plan={offer.suggested_plan.slug}"

                    subject = translation(
                        settings.lang,
                        en=f"Your 4Geeks plan financing to {plan.slug if plan else 'plan'} has been discontinued",
                        es=f"Tu financiamiento 4Geeks a {plan.slug if plan else 'plan'} ha sido descontinuado",
                    )

                    obj = {"SUBJECT": subject}

                    if link:
                        button = translation(
                            settings.lang,
                            en="See suggested plan",
                            es="Ver plan sugerido",
                        )
                        obj["LINK"] = link
                        obj["BUTTON"] = button

                        message = translation(
                            settings.lang,
                            en="Your plan financing contract remains active and charges will continue as scheduled. This catalog plan has been discontinued and may be removed in the future, so we are sharing suggested alternatives.",
                            es="Tu contrato de financiamiento sigue activo y los cobros continuaran segun lo programado. Este plan del catalogo fue descontinuado y podria eliminarse en el futuro, por eso te compartimos alternativas sugeridas.",
                        )
                    else:
                        message = translation(
                            settings.lang,
                            en="Your plan financing contract remains active and charges will continue as scheduled. This catalog plan has been discontinued and may be removed in the future.",
                            es="Tu contrato de financiamiento sigue activo y los cobros continuaran segun lo programado. Este plan del catalogo fue descontinuado y podria eliminarse en el futuro.",
                        )

                    obj["MESSAGE"] = message

                    try:
                        notify_actions.send_email_message(
                            "message",
                            plan_financing.user.email,
                            obj,
                            academy=plan_financing.academy,
                        )
                        cache.set(notification_cache_key, True, 60 * 60 * 24 * 365)
                    except Exception as e:
                        logger.error(
                            "Failed sending discontinued plan financing warning for %s: %s",
                            plan_financing.id,
                            str(e),
                            exc_info=True,
                        )

            # A discontinued catalog plan must not invalidate an already-signed financing contract.
            # Deleted plans stop future charges, but financing status must not be forced to DEPRECATED
            # because the model explicitly forbids that status.
            if plan_financing.plans.filter(status=Plan.Status.DELETED).exists():
                # Send notification to user
                plan = plan_financing.plans.first()
                link = None

                if plan and (offer := PlanOffer.objects.filter(original_plan=plan).first()):
                    link = f"{get_app_url()}/checkout?plan={offer.suggested_plan.slug}"

                subject = translation(
                    settings.lang,
                    en=f"Your 4Geeks plan financing to {plan.slug if plan else 'plan'} is no longer available",
                    es=f"Tu financiamiento 4Geeks a {plan.slug if plan else 'plan'} ya no esta disponible",
                )

                obj = {
                    "SUBJECT": subject,
                }

                if link:
                    button = translation(
                        settings.lang,
                        en="See suggested plan",
                        es="Ver plan sugerido",
                    )
                    obj["LINK"] = link
                    obj["BUTTON"] = button

                    message = translation(
                        settings.lang,
                        en="We regret to inform you that your 4Geeks plan financing is no longer available. Please check our suggested plans for alternatives.",
                        es="Lamentamos informarte que tu financiamiento 4Geeks ya no esta disponible. Por favor, revisa nuestros planes sugeridos para alternativas.",
                    )
                else:
                    message = translation(
                        settings.lang,
                        en="We regret to inform you that your 4Geeks plan financing is no longer available.",
                        es="Lamentamos informarte que tu financiamiento 4Geeks ya no esta disponible.",
                    )

                obj["MESSAGE"] = message

                try:
                    notify_actions.send_email_message(
                        "message",
                        plan_financing.user.email,
                        obj,
                        academy=plan_financing.academy,
                    )
                except Exception as e:
                    logger.error(
                        "Failed sending deleted plan financing notification for %s: %s",
                        plan_financing.id,
                        str(e),
                        exc_info=True,
                    )
                raise AbortTask(f"PlanFinancing with id {plan_financing.id} has deleted plans")

            invoices = plan_financing.invoices.filter(bag__was_delivered=True).order_by("created_at")
            first_invoice = invoices.first()

            if first_invoice is None:
                msg = f"No invoices found for PlanFinancing with id {plan_financing_id}"
                plan_financing.status = "ERROR"
                plan_financing.status_message = msg
                plan_financing.save()

                raise AbortTask(msg)

            # Contract source of truth: monthly_price.
            amount = float(plan_financing.monthly_price or 0)
            if amount <= 0:
                # Legacy fallback for old records where monthly_price was not reliably populated.
                # Derive the display price per installment from the first invoice amount, but exclude reward coupons.
                amount = first_invoice.amount
                coupons = first_invoice.bag.coupons.all() if first_invoice.bag else []

                reward_coupons = [
                    coupon
                    for coupon in coupons
                    if coupon
                    and coupon.allowed_user_id is not None
                    and coupon.referral_type == Coupon.Referral.NO_REFERRAL
                ]

                for coupon in reward_coupons:
                    v = coupon.discount_value or 0

                    if coupon.discount_type == Coupon.Discount.PERCENT_OFF:
                        factor = 1 - v
                        if factor > 0:
                            amount /= factor
                    elif coupon.discount_type == Coupon.Discount.FIXED_PRICE:
                        amount += v

            installments = plan_financing.how_many_installments

            # installments_paid is the authoritative counter of closed billing cycles.
            remaining_installments = installments - plan_financing.installments_paid

            if remaining_installments > 0:
                # ── Credit-first: consume CreditLedgerEntry balance before hitting Stripe ────────
                credit_balance = actions.get_credit_balance(plan_financing)
                amount_owed = float(amount or 0)
                _credit_to_consume = 0.0
                credit_covered = False

                if credit_balance >= amount_owed - 1e-9 and amount_owed > 0:
                    # Credit covers the full installment.
                    # No new invoice — the cash was already documented when the user deposited.
                    # We record the ledger consumption and increment the authoritative counter.
                    CreditLedgerEntry.objects.create(
                        user=plan_financing.user,
                        scope=CreditLedgerEntry.Scope.PLAN_FINANCING,
                        plan_financing=plan_financing,
                        amount=-amount_owed,
                        entry_type=CreditLedgerEntry.EntryType.CREDIT_CONSUMED,
                        notes="Automatic charge covered by accumulated credit",
                    )
                    plan_financing.installments_paid += 1
                    credit_covered = True

                else:
                    if credit_balance > 1e-9 and amount_owed > 0:
                        # Partial credit — reduce the Stripe charge by the available credit.
                        _credit_to_consume = credit_balance
                        amount = amount_owed - credit_balance

                    # Look for existing payment that hasn't been delivered yet
                    invoice = (
                        plan_financing.invoices.filter(
                            paid_at__lte=utc_now, status="FULFILLED", bag__was_delivered=False
                        )
                        .order_by("-paid_at")
                        .first()
                    )

                    if invoice:
                        bag = invoice.bag

                    else:
                        if plan_financing.externally_managed:
                            message = translation(
                                settings.lang,
                                en="Please make your payment in your academy or use another payment method",
                                es="Por favor realiza tu pago en tu academia o utiliza otro método de pago",
                            )

                            button = translation(
                                settings.lang,
                                en="Renew with another method",
                                es="Renovar con otro método",
                            )
                            alert_payment_issue(message, button)

                            if plan_financing.status not in no_charge_statuses:
                                manager = schedule_task(charge_plan_financing, "1d")
                                if not manager.exists(plan_financing.id):
                                    manager.call(plan_financing.id)

                            raise AbortTask(f"Payment to PlanFinancing {plan_financing_id} failed")
                        else:
                            try:
                                bag = actions.get_bag_from_plan_financing(plan_financing, settings)
                            except Exception as e:
                                plan_financing.status = "ERROR"
                                plan_financing.status_message = str(e)
                                plan_financing.save()

                                if plan_financing.status not in no_charge_statuses:
                                    manager = schedule_task(charge_plan_financing, "1d")
                                    if not manager.exists(plan_financing.id):
                                        manager.call(plan_financing.id)

                                raise AbortTask(f"Error getting bag from plan financing {plan_financing_id}: {e}")

                            try:
                                s = Stripe(academy=plan_financing.academy)
                                s.set_language(settings.lang)
                                invoice = s.pay(plan_financing.user, bag, amount, currency=bag.currency)
                                invoice.amount_breakdown = actions.calculate_invoice_breakdown(
                                    bag,
                                    invoice,
                                    settings.lang,
                                    how_many_installments=plan_financing.how_many_installments,
                                )
                                invoice.save(update_fields=["amount_breakdown"])

                            except Exception:
                                message = translation(
                                    settings.lang,
                                    en="Your payment with credit card was declined, please update your card or use another payment method",
                                    es="Tu pago con tarjeta de crédito fue rechazado, por favor update tu tarjeta o utiliza otro método de pago",
                                )

                                button = translation(
                                    settings.lang,
                                    en="Change payment method",
                                    es="Cambiar método de pago",
                                )
                                alert_payment_issue(message, button)

                                manager = schedule_task(charge_plan_financing, "1d")
                                if not manager.exists(plan_financing.id):
                                    manager.call(plan_financing.id)

                                raise AbortTask(f"Payment to PlanFinancing {plan_financing_id} failed")

                    # If partial credit was applied alongside a successful Stripe charge, record it.
                    if _credit_to_consume > 1e-9:
                        CreditLedgerEntry.objects.create(
                            user=plan_financing.user,
                            scope=CreditLedgerEntry.Scope.PLAN_FINANCING,
                            plan_financing=plan_financing,
                            amount=-_credit_to_consume,
                            entry_type=CreditLedgerEntry.EntryType.CREDIT_CONSUMED,
                            notes="Partial credit applied to reduce automatic charge",
                        )

                    plan_financing.invoices.add(invoice)
                    plan_financing.installments_paid += 1

                    if bag:
                        bag.was_delivered = True
                        bag.save()

                    notify_actions.send_email_message(
                        "message",
                        invoice.user.email,
                        {
                            "SUBJECT": translation(
                                settings.lang,
                                en="Your installment at 4Geeks was successfully charged",
                                es="Tu cuota en 4Geeks fue cobrada exitosamente",
                            ),
                            "MESSAGE": translation(
                                settings.lang,
                                en=f"The amount was {invoice.currency.format_price(invoice.amount)}",
                                es=f"El monto fue {invoice.currency.format_price(invoice.amount)}",
                            ),
                            "BUTTON": translation(settings.lang, en="See the invoice", es="Ver la factura"),
                            "LINK": f"{get_app_url()}/paymentmethod",
                        },
                        academy=plan_financing.academy,
                    )

                # Re-derive remaining after incrementing installments_paid.
                remaining_installments = installments - plan_financing.installments_paid

                if utc_now > plan_financing.valid_until:
                    plan_financing.valid_until = utc_now + relativedelta(months=remaining_installments)

            delta = relativedelta(months=1)

            while utc_now >= plan_financing.next_payment_at + delta:
                delta += relativedelta(months=1)

            plan_financing.next_payment_at += delta
            plan_financing.status = "ACTIVE" if remaining_installments > 0 else "FULLY_PAID"
            plan_financing.status_message = None
            plan_financing.save()

            renew_plan_financing_consumables.delay(plan_financing.id)

            # Schedule next charge if plan is still active and has remaining installments
            days_until_next_payment = (plan_financing.next_payment_at - utc_now).days
            if days_until_next_payment > 0:  # Only schedule if there are days remaining
                manager = schedule_task(charge_plan_financing, f"{days_until_next_payment}d")
                if not manager.exists(plan_financing_id):
                    manager.call(plan_financing_id)

            if early_renewal_window_days > 0 and days_until_next_payment > early_renewal_window_days:
                notification_day = days_until_next_payment - early_renewal_window_days
                manager = schedule_task(notify_plan_financing_renewal, f"{notification_day}d")
                if not manager.exists(plan_financing_id):
                    manager.call(plan_financing_id)

    except LockError:
        raise RetryTask("Could not acquire lock for activity, operation timed out.")


@task(bind=True, priority=TaskPriority.WEB_SERVICE_PAYMENT.value)
def build_service_stock_scheduler_from_subscription(
    self,
    subscription_id: int,
    user_id: Optional[int] = None,
    update_mode: Optional[bool] = False,
    seat_id: Optional[int] = None,
    service_ids: Optional[list[int]] = None,
    **_: Any,
):
    """Build service stock scheduler for a subscription."""

    logger.info(f"Starting build_service_stock_scheduler_from_subscription for subscription {subscription_id}")

    def build_schedulers(allow_team=None, team_for_billing=None):
        """
        Build ServiceStockScheduler rows for a subscription according to the context.

        This helper is used by `build_service_stock_scheduler_from_subscription` to create
        schedulers for both subscription-level and plan-level service items. It supports
        three issuance contexts controlled by the arguments and outer scope state:

        - Owner context (no seat, no team):
          When `allow_team is None`, create schedulers for ALL items (team-allowed and non-team).
          When `allow_team is False`, create ONLY non-team items for the owner.

        - Team-owned context (PER_TEAM):
          When `allow_team is True` and `team_for_billing` is provided, create schedulers for
          team-allowed items with `subscription_billing_team` set to that team and `user=None`
          (consumables will be issued for the team, not a specific user).

        - Seat context (PER_SEAT):
          When building for a seat (outer `subscription_seat` is not None), this function will
          create schedulers only for team-allowed items linked to that seat. The billing team is
          derived from the seat, and the seat is recorded in `subscription_seat`.

        Parameters
        - allow_team: Optional[bool]
          * None  -> include all items (owner context, used when no seats exist)
          * False -> include only non-team items (owner context)
          * True  -> include only team-allowed items (team/seat context)

        - team_for_billing: Optional[SubscriptionBillingTeam]
          Team to attach when creating team-owned schedulers in PER_TEAM context. If building for a
          specific seat, this is ignored and derived from `subscription_seat`.

        Notes
        - Relies on outer-scope variables: `subscription`, `subscription_seat`, `utc_now`, and
          `update_mode`.
        - When `update_mode` is False, this function triggers a renewal via
          `renew_subscription_consumables.delay(subscription.id, seat_id=seat_id)` after creating
          schedulers so consumables are issued immediately.
        """
        # Determine billing team for schedulers
        billing_team = None
        if team_for_billing is not None:
            billing_team = team_for_billing
        elif subscription_seat:
            # when building per-seat, derive team from the seat
            billing_team = subscription_seat.billing_team

        for handler in SubscriptionServiceItem.objects.filter(subscription=subscription).select_related("service_item"):
            if service_ids and handler.service_item.service_id not in service_ids:
                continue
            # Filter by team-allowed depending on context; applies to owner, team-owned, or seat
            if allow_team is not None and handler.service_item.is_team_allowed is not allow_team:
                continue
            unit = handler.service_item.renew_at
            unit_type = handler.service_item.renew_at_unit
            delta = actions.calculate_relative_delta(unit, unit_type)
            valid_until = utc_now + delta

            if subscription.next_payment_at and valid_until > subscription.next_payment_at:
                valid_until = subscription.next_payment_at

            if subscription.valid_until and valid_until > subscription.valid_until:
                valid_until = subscription.valid_until

            # Do not set both seat and billing team simultaneously
            ServiceStockScheduler.objects.get_or_create(
                subscription_handler=handler,
                subscription_seat=subscription_seat,
                subscription_billing_team=(billing_team if subscription_seat is None else None),
            )

        for plan in subscription.plans.all():
            for handler in PlanServiceItem.objects.filter(plan=plan).select_related("service_item"):
                if service_ids and handler.service_item.service_id not in service_ids:
                    continue
                # Filter by team-allowed depending on context; applies to owner, team-owned, or seat
                if allow_team is not None and handler.service_item.is_team_allowed is not allow_team:
                    continue
                unit = handler.service_item.renew_at
                unit_type = handler.service_item.renew_at_unit
                delta = actions.calculate_relative_delta(unit, unit_type)
                valid_until = utc_now + delta

                if valid_until > subscription.next_payment_at:
                    valid_until = subscription.next_payment_at

                if subscription.valid_until and valid_until > subscription.valid_until:
                    valid_until = subscription.valid_until

                handler, _ = PlanServiceItemHandler.objects.get_or_create(subscription=subscription, handler=handler)

                # Do not set both seat and billing team simultaneously
                ServiceStockScheduler.objects.get_or_create(
                    plan_handler=handler,
                    subscription_seat=subscription_seat,
                    subscription_billing_team=(billing_team if subscription_seat is None else None),
                )

        if not update_mode:
            renew_subscription_consumables.delay(subscription.id, seat_id=seat_id, service_ids=service_ids)

    team = None
    subscription_seat = None
    if seat_id:
        # SubscriptionSeat does not link directly to Subscription; it links via billing_team
        subscription_seat = SubscriptionSeat.objects.filter(
            billing_team__subscription__id=subscription_id, id=seat_id
        ).first()
        if not subscription_seat:
            raise RetryTask(f"SubscriptionSeat with id {seat_id} not found")

    k = {
        "subscription": "user__id",
        # service items of
        "handlers": {
            "of_subscription": "subscription_handler__subscription__user__id",
            "of_plan": "plan_handler__subscription__user__id",
        },
    }
    # seat_service_item

    additional_args = {
        "subscription": {k["subscription"]: user_id} if user_id else {},
        # service items of
        "handlers": {
            "of_subscription": {
                k["handlers"]["of_subscription"]: user_id,
            },
            "of_plan": {
                k["handlers"]["of_plan"]: user_id,
            },
        },
    }

    if not (subscription := Subscription.objects.filter(id=subscription_id, **additional_args["subscription"]).first()):
        raise RetryTask(f"Subscription with id {subscription_id} not found")

    # Determine if subscription has seats configured
    has_seats = bool(subscription.seat_service_item and subscription.seat_service_item.how_many > 0)

    # When seats exist and we are building for the owner (no seat_id), we must:
    # - If PER_TEAM: create team-owned schedulers for team-allowed items and owner schedulers for non-team items
    # - If PER_SEAT: create owner schedulers ONLY for non-team items, then schedule per-seat builds for team items
    utc_now = timezone.now()
    if not seat_id and has_seats:
        # `defaults` is only valid for get_or_create; use a simple filter here
        team = SubscriptionBillingTeam.objects.filter(subscription=subscription).first()
        if not team:
            raise RetryTask(f"SubscriptionBillingTeam with id {subscription_id} not found")

        if team.consumption_strategy == SubscriptionBillingTeam.ConsumptionStrategy.PER_TEAM:
            # Build team-owned schedulers for team-allowed items
            update_mode = True
            build_schedulers(True, team_for_billing=team)
            # Build owner schedulers for non-team items
            update_mode = False
            build_schedulers(False, team_for_billing=None)
            return

        utc_now = timezone.now()
        # TODO: it changed the scheduler from None to False, check if this is the correct behavior
        # Build owner schedulers for non-team items only; team items will be handled per-seat
        build_schedulers(False, team_for_billing=None)
        # Schedule per-seat builds (these runs will create schedulers only for team-allowed items)
        for seat in SubscriptionSeat.objects.filter(billing_team=team):
            build_service_stock_scheduler_from_subscription.delay(
                subscription_id, seat_id=seat.id, service_ids=service_ids
            )

        return

    # If building for a seat, only build team-allowed items; for owner without seats, build all
    build_schedulers(True if seat_id is not None else None)


@task(bind=True, priority=TaskPriority.WEB_SERVICE_PAYMENT.value)
def build_service_stock_scheduler_from_plan_financing(
    self,
    plan_financing_id: int,
    seat_id: Optional[int] = None,
    user_id: Optional[int] = None,
    service_ids: Optional[list[int]] = None,
    **_: Any,
):
    """Build service stock scheduler for a plan financing."""

    logger.info(f"Starting build_service_stock_scheduler_from_plan_financing for subscription {plan_financing_id}")

    filters = {"id": plan_financing_id}
    if user_id:
        filters["user__id"] = user_id

    plan_financing = PlanFinancing.objects.filter(**filters).first()
    if not plan_financing:
        raise RetryTask(f"PlanFinancing with id {plan_financing_id} not found")

    team = getattr(plan_financing, "team", None)
    per_team_strategy = team and team.consumption_strategy == PlanFinancingTeam.ConsumptionStrategy.PER_TEAM

    seat_scope: list[PlanFinancingSeat] = []
    if team:
        seat_queryset = team.seats.filter(is_active=True)
        if seat_id:
            seat = seat_queryset.filter(id=seat_id).first()
            if not seat and not per_team_strategy:
                raise RetryTask(f"PlanFinancingSeat with id {seat_id} not found")
            if seat:
                seat_scope = [seat]
        if not seat_scope and not per_team_strategy:
            seat_scope = list(seat_queryset)

    def upsert_scheduler(
        handler_obj: PlanServiceItemHandler,
        valid_until: datetime,
        *,
        seat: PlanFinancingSeat | None = None,
    ) -> None:
        scheduler, created = ServiceStockScheduler.objects.get_or_create(
            plan_handler=handler_obj,
            plan_financing_seat=seat,
            plan_financing_team=team if (per_team_strategy and seat is None and team) else None,
            defaults={"valid_until": valid_until},
        )

        update_fields: list[str] = []
        if not created and scheduler.valid_until != valid_until:
            scheduler.valid_until = valid_until
            update_fields.append("valid_until")

        if per_team_strategy and team and scheduler.plan_financing_team_id != team.id:
            scheduler.plan_financing_team = team
            update_fields.append("plan_financing_team")

        if not per_team_strategy and scheduler.plan_financing_team_id is not None:
            scheduler.plan_financing_team = None
            update_fields.append("plan_financing_team")

        if not created and update_fields:
            scheduler.save(update_fields=update_fields)

    def compute_valid_until(plan_service_item: PlanServiceItem) -> datetime:
        unit = plan_service_item.service_item.renew_at
        unit_type = plan_service_item.service_item.renew_at_unit
        delta = actions.calculate_relative_delta(unit, unit_type)
        valid_until = plan_financing.created_at + delta

        if plan_financing.status != PlanFinancing.Status.FULLY_PAID and valid_until > plan_financing.next_payment_at:
            valid_until = plan_financing.next_payment_at

        if plan_financing.plan_expires_at and valid_until > plan_financing.plan_expires_at:
            valid_until = plan_financing.plan_expires_at

        if (
            plan_financing.valid_until
            and valid_until > plan_financing.valid_until
            and plan_financing.status != PlanFinancing.Status.FULLY_PAID
        ):
            valid_until = plan_financing.valid_until

        if plan_financing.status == PlanFinancing.Status.FULLY_PAID:
            utc_now = timezone.now()
            valid_until = utc_now + delta

        return valid_until

    for plan in plan_financing.plans.all():
        plan_service_items = PlanServiceItem.objects.filter(plan=plan).select_related("service_item")
        if service_ids:
            plan_service_items = plan_service_items.filter(service_item__service_id__in=service_ids)

        for plan_service_item in plan_service_items:
            handler_obj, _ = PlanServiceItemHandler.objects.get_or_create(
                plan_financing=plan_financing, handler=plan_service_item
            )
            valid_until = compute_valid_until(plan_service_item)

            if team and per_team_strategy:
                upsert_scheduler(handler_obj, valid_until)
            elif seat_scope:
                for seat in seat_scope:
                    upsert_scheduler(handler_obj, valid_until, seat=seat)
            else:
                upsert_scheduler(handler_obj, valid_until)

    if seat_id:
        renew_plan_financing_consumables.delay(plan_financing.id, seat_id=seat_id, service_ids=service_ids)
    else:
        renew_plan_financing_consumables.delay(plan_financing.id, service_ids=service_ids)


@task(bind=False, priority=TaskPriority.WEB_SERVICE_PAYMENT.value)
def build_subscription(
    bag_id: int,
    invoice_id: int,
    start_date: Optional[datetime] = None,
    conversion_info: Optional[str] = "",
    externally_managed: bool = False,
    **_: Any,
):
    logger.info(f"Starting build_subscription for bag {bag_id}")

    if not (bag := Bag.objects.filter(id=bag_id, status="PAID", was_delivered=False).first()):
        raise RetryTask(f"Bag with id {bag_id} not found")

    if not (invoice := Invoice.objects.filter(id=invoice_id, status="FULFILLED").first()):
        raise RetryTask(f"Invoice with id {invoice_id} not found")

    months = 1
    pay_every_unit = "MONTH"

    if bag.chosen_period == "QUARTER":
        months = 3
        pay_every_unit = "MONTH"
        pay_every = 3

    elif bag.chosen_period == "HALF":
        months = 6
        pay_every_unit = "MONTH"
        pay_every = 6

    elif bag.chosen_period == "YEAR":
        months = 12
        pay_every_unit = "YEAR"
        pay_every = 1
    else:
        pay_every = 1

    plan = bag.plans.first()

    if plan:
        cohort_set = plan.cohort_set
        event_type_set = plan.event_type_set
        mentorship_service_set = plan.mentorship_service_set

    else:
        cohort_set = None
        event_type_set = None
        mentorship_service_set = None

    subscription_start_at = start_date or invoice.paid_at
    if isinstance(subscription_start_at, str):
        subscription_start_at = datetime.fromisoformat(subscription_start_at)

    next_payment_at = subscription_start_at + relativedelta(months=months)

    parsed_conversion_info = ast.literal_eval(conversion_info) if conversion_info not in [None, ""] else None
    subscription = Subscription.objects.create(
        user=bag.user,
        paid_at=invoice.paid_at,
        academy=bag.academy,
        selected_cohort_set=cohort_set,
        selected_event_type_set=event_type_set,
        selected_mentorship_service_set=mentorship_service_set,
        valid_until=None,
        next_payment_at=next_payment_at,
        status="ACTIVE",
        conversion_info=parsed_conversion_info,
        pay_every_unit=pay_every_unit,
        pay_every=pay_every,
        currency=bag.currency or bag.academy.main_currency,  # Ensure currency is passed from bag
        seat_service_item=bag.seat_service_item,
        externally_managed=externally_managed,
    )

    if bag.seat_service_item and bag.seat_service_item.how_many > 0:
        subscription.seat_service_item = bag.seat_service_item
        subscription.save()

    subscription.plans.set(bag.plans.all())

    # Persist add-ons (bag.service_items) into the subscription so they renew and can be billed monthly
    for service_item in bag.service_items.all():
        SubscriptionServiceItem.objects.get_or_create(subscription=subscription, service_item=service_item)

    # Add coupons from the bag to the subscription
    bag_coupons = bag.coupons.all()
    if bag_coupons.exists():
        subscription.coupons.set(bag_coupons)
        # Increment usage counters for coupons
        now = timezone.now()
        Coupon.objects.filter(id__in=[c.id for c in bag_coupons]).update(
            times_used=F("times_used") + 1, last_used_at=now
        )
        logger.info(f"Added {bag_coupons.count()} coupons to subscription {subscription.id}")

    subscription.save()
    subscription.invoices.add(invoice)

    bag.was_delivered = True
    bag.save()

    plan = bag.plans.first()

    if plan and subscription.seat_service_item and subscription.seat_service_item.how_many > 0:
        team, _ = SubscriptionBillingTeam.objects.get_or_create(
            subscription=subscription,
            defaults={
                "name": f"Team {subscription.id}",
                "additional_seats": subscription.seat_service_item.how_many,
                "consumption_strategy": (
                    # if BOTH is implemented should be required to get the strategy from the bag
                    Plan.ConsumptionStrategy.PER_SEAT
                    if plan.consumption_strategy == Plan.ConsumptionStrategy.BOTH
                    else plan.consumption_strategy
                ),
            },
        )

        SubscriptionSeat.objects.get_or_create(
            billing_team=team,
            user=bag.user,
            defaults={"email": subscription.user.email, "is_active": True},
        )

    build_service_stock_scheduler_from_subscription.delay(subscription.id)

    # Schedule the next charge task based on days until next_payment_at
    days_until_next_payment = (next_payment_at - subscription.paid_at).days
    manager = schedule_task(charge_subscription, f"{days_until_next_payment}d")
    if not manager.exists(subscription.id):
        manager.call(subscription.id)

    payment_settings = AcademyPaymentSettings.objects.filter(academy=subscription.academy).first()
    early_renewal_window_days = payment_settings.early_renewal_window_days if payment_settings else 0

    if early_renewal_window_days > 0 and days_until_next_payment > early_renewal_window_days:
        notification_day = days_until_next_payment - early_renewal_window_days
        manager = schedule_task(notify_subscription_renewal, f"{notification_day}d")
        if not manager.exists(subscription.id):
            manager.call(subscription.id)

    logger.info(f"Subscription was created with id {subscription.id}")


@task(bind=False, priority=TaskPriority.WEB_SERVICE_PAYMENT.value)
def build_plan_financing(
    bag_id: int,
    invoice_id: int,
    is_free: bool = False,
    conversion_info: Optional[str] = "",
    cohorts: Optional[list[str]] = None,
    externally_managed: bool = False,
    principal_amount: Optional[float] = None,
    initial_payment_amount: Optional[float] = None,
    initial_payment_notes: Optional[str] = None,
    grace_period_duration: int = 0,
    grace_period_duration_unit: str = "MONTH",
    **_: Any,
):
    logger.info(f"Starting build_plan_financing for bag {bag_id}")

    if cohorts is None:
        cohorts = []

    if not (bag := Bag.objects.filter(id=bag_id, status="PAID", was_delivered=False).first()):
        raise RetryTask(f"Bag with id {bag_id} not found")

    if not (
        invoice := Invoice.objects.filter(id=invoice_id, status="FULFILLED").select_related("payment_method").first()
    ):
        raise RetryTask(f"Invoice with id {invoice_id} not found")

    zero_initial_payment = initial_payment_amount is not None and principal_amount is not None
    if not is_free and not invoice.amount and not zero_initial_payment:
        raise AbortTask(f"An invoice without amount is prohibited (id: {invoice_id})")

    if initial_payment_notes is not None:
        invoice.invoice_notes = initial_payment_notes
        invoice.save(update_fields=["invoice_notes"])

    utc_now = timezone.now()
    months = bag.how_many_installments
    plans = bag.plans.all()
    delta = relativedelta(0)

    for plan in plans:
        unit = plan.time_of_life
        unit_type = plan.time_of_life_unit

        if not unit or not unit_type:
            continue

        new_delta = actions.calculate_relative_delta(unit, unit_type)
        if utc_now + new_delta > utc_now + delta:
            delta = new_delta

    plan = bag.plans.first()

    if plan:
        cohort_set = plan.cohort_set
        event_type_set = plan.event_type_set
        mentorship_service_set = plan.mentorship_service_set

    else:
        cohort_set = None
        event_type_set = None
        mentorship_service_set = None

    if cohorts:
        cohorts = Cohort.objects.filter(slug__in=cohorts)

    grace_delta = (
        actions.calculate_relative_delta(grace_period_duration, grace_period_duration_unit)
        if grace_period_duration
        else relativedelta(0)
    )
    next_payment_at = (
        invoice.paid_at + grace_delta if grace_period_duration else invoice.paid_at + relativedelta(months=1)
    )

    parsed_conversion_info = ast.literal_eval(conversion_info) if conversion_info not in [None, ""] else None
    # principal_amount allows separating the recurring amount (plan base)
    # from any one-shot components (like plan_addons) that were included
    # in the first invoice. When provided, it is used as the monthly_price
    # instead of the invoice.amount.
    monthly_price = principal_amount if principal_amount is not None else invoice.amount
    # Last installment due date: (months - 1) periods after the first scheduled payment.
    # Must use next_payment_at (includes grace) so valid_until shifts with grace; do not anchor only to paid_at.
    valid_until = next_payment_at + relativedelta(months=max(months - 1, 0))

    # If a third party (e.g. Klarna/Affirm) manages installments, the invoice amount is the full financing total and all installments count as paid.
    is_full_financing_amount = (
        bag.how_many_installments > 0
        and initial_payment_amount is None
        and invoice.payment_method is not None
        and invoice.payment_method.is_financing_managed_by_provider
    )

    if is_full_financing_amount:
        initial_installments_paid = bag.how_many_installments
        financing_status = PlanFinancing.Status.FULLY_PAID
    else:
        initial_installments_paid = 0 if initial_payment_amount is not None else 1
        financing_status = PlanFinancing.Status.ACTIVE

    financing = PlanFinancing.objects.create(
        user=bag.user,
        how_many_installments=bag.how_many_installments,
        installments_paid=initial_installments_paid,
        next_payment_at=next_payment_at,
        academy=bag.academy,
        selected_cohort_set=cohort_set,
        selected_event_type_set=event_type_set,
        selected_mentorship_service_set=mentorship_service_set,
        valid_until=valid_until,
        plan_expires_at=invoice.paid_at + delta,
        monthly_price=monthly_price,
        initial_payment_amount=initial_payment_amount,
        grace_period_duration=grace_period_duration,
        grace_period_duration_unit=grace_period_duration_unit,
        status=financing_status,
        conversion_info=parsed_conversion_info,
        currency=bag.currency or bag.academy.main_currency,  # Ensure currency is passed from bag
        seat_service_item=bag.seat_service_item,
        externally_managed=externally_managed,
    )

    if bag.seat_service_item and bag.seat_service_item.how_many > 0:
        financing.seat_service_item = bag.seat_service_item
        financing.save()

    if cohorts:
        financing.joined_cohorts.set(cohorts)

    financing.plans.set(plans)

    # Add coupons from the bag to the plan financing
    bag_coupons = bag.coupons.all()
    if bag_coupons.exists():
        financing.coupons.set(bag_coupons)
        # Increment usage counters for coupons
        now = timezone.now()
        Coupon.objects.filter(id__in=[c.id for c in bag_coupons]).update(
            times_used=F("times_used") + 1, last_used_at=now
        )
        logger.info(f"Added {bag_coupons.count()} coupons to plan financing {financing.id}")

    financing.save()
    financing.invoices.add(invoice)

    if initial_payment_amount is not None and invoice.invoice_kind != Invoice.InvoiceKind.MANUAL_DEPOSIT:
        invoice.invoice_kind = Invoice.InvoiceKind.MANUAL_DEPOSIT
        invoice.save(update_fields=["invoice_kind"])

    bag.was_delivered = True
    bag.save()

    build_service_stock_scheduler_from_plan_financing.delay(financing.id)

    if not is_full_financing_amount:
        # Schedule monthly charges based on days until next payment
        days_until_next_payment = (next_payment_at - invoice.paid_at).days
        manager = schedule_task(charge_plan_financing, f"{days_until_next_payment}d")
        if not manager.exists(financing.id):
            manager.call(financing.id)

        if days_until_next_payment > 2:
            notification_day = days_until_next_payment - 2
            manager = schedule_task(notify_plan_financing_renewal, f"{notification_day}d")
            if not manager.exists(financing.id):
                manager.call(financing.id)

    logger.info(f"PlanFinancing was created with id {financing.id}")


@task(bind=True, priority=TaskPriority.WEB_SERVICE_PAYMENT.value)
def build_free_subscription(self, bag_id: int, invoice_id: int, conversion_info: Optional[str] = "", **_: Any):
    logger.info(f"Starting build_free_subscription for bag {bag_id}")

    if not (bag := Bag.objects.filter(id=bag_id, status="PAID", was_delivered=False).first()):
        raise RetryTask(f"Bag with id {bag_id} not found")

    if not (invoice := Invoice.objects.filter(id=invoice_id, status="FULFILLED").first()):
        raise RetryTask(f"Invoice with id {invoice_id} not found")

    if invoice.amount != 0:
        raise AbortTask(f"The invoice with id {invoice_id} is invalid for a free subscription")

    plans = bag.plans.all()

    if not plans:
        raise AbortTask(f"Not have plans to associated to this free subscription in the bag {bag_id}")

    for plan in plans:
        is_free_trial = True
        unit = plan.trial_duration
        unit_type = plan.trial_duration_unit

        if not unit:
            is_free_trial = False
            unit = plan.time_of_life
            unit_type = plan.time_of_life_unit

        delta = actions.calculate_relative_delta(unit, unit_type)

        until = invoice.paid_at + delta

        if plan:
            cohort_set = plan.cohort_set
            event_type_set = plan.event_type_set
            mentorship_service_set = plan.mentorship_service_set

        else:
            cohort_set = None
            event_type_set = None
            mentorship_service_set = None

        if is_free_trial:
            extra = {
                "status": "FREE_TRIAL",
                "valid_until": until,
            }

        elif not is_free_trial and plan.is_renewable:
            extra = {
                "status": "ACTIVE",
                "valid_until": None,
            }

        else:
            extra = {
                "status": "ACTIVE",
                "valid_until": until,
            }

        parsed_conversion_info = ast.literal_eval(conversion_info) if conversion_info not in [None, ""] else None
        subscription = Subscription.objects.create(
            user=bag.user,
            paid_at=invoice.paid_at,
            academy=bag.academy,
            selected_cohort_set=cohort_set,
            selected_event_type_set=event_type_set,
            selected_mentorship_service_set=mentorship_service_set,
            next_payment_at=until,
            conversion_info=parsed_conversion_info,
            currency=bag.currency or bag.academy.main_currency,  # Ensure currency is passed from bag
            **extra,
        )

        subscription.plans.add(plan)

        # Add coupons from the bag to the subscription
        bag_coupons = bag.coupons.all()
        if bag_coupons.exists():
            subscription.coupons.set(bag_coupons)
            logger.info(f"Added {bag_coupons.count()} coupons to free subscription {subscription.id}")

        subscription.save()
        subscription.invoices.add(invoice)

        build_service_stock_scheduler_from_subscription.delay(subscription.id)

        logger.info(f"Free subscription was created with id {subscription.id} for plan {plan.id}")

    bag.was_delivered = True
    bag.save()


@task(bind=True, priority=TaskPriority.WEB_SERVICE_PAYMENT.value)
def end_the_consumption_session(self, consumption_session_id: int, how_many: float = 1.0, **_: Any):
    logger.info(f"Starting end_the_consumption_session for ConsumptionSession {consumption_session_id}")

    session = ConsumptionSession.objects.filter(id=consumption_session_id).first()
    if not session:
        raise AbortTask(f"ConsumptionSession with id {consumption_session_id} not found")

    if session.status != "PENDING":
        raise AbortTask(f"ConsumptionSession with id {consumption_session_id} already processed")

    consumable = session.consumable
    consume_service.send_robust(instance=consumable, sender=consumable.__class__, how_many=how_many)

    session.was_discounted = True
    session.status = "DONE"
    session.save()


# TODO: this task is not being used, if you will use this task, you need to take in consideration
# you need fix the logic about the consumable valid until, maybe this must be removed
@task(bind=True, priority=TaskPriority.WEB_SERVICE_PAYMENT.value)
def build_consumables_from_bag(bag_id: int, **_: Any):
    logger.info(f"Starting build_consumables_from_bag for bag {bag_id}")

    if not (bag := Bag.objects.filter(id=bag_id, status="PAID", was_delivered=False).first()):
        raise RetryTask(f"Bag with id {bag_id} not found")

    mentorship_service_set = bag.selected_mentorship_service_sets.first()
    event_type_set = bag.selected_event_type_sets.first()

    if [mentorship_service_set, event_type_set].count(None) != 1:
        raise AbortTask(f"Bag with id {bag_id} not have a resource associated")

    consumables = []
    for service_item in bag.service_items.all():
        kwargs = {}
        if service_item.service_item_type == "MENTORSHIP_SERVICE_SET":
            kwargs["mentorship_service_set"] = mentorship_service_set

        if service_item.service_item_type == "EVENT_TYPE_SET":
            kwargs["event_type_set"] = event_type_set

        if not kwargs:
            raise AbortTask(f"Bag with id {bag_id} have a resource associated opposite to the service item type")

        consumables.append(
            Consumable(
                service_item=service_item,
                unit_type=service_item.unit_type,
                how_many=service_item.how_many,
                user=bag.user,
                **kwargs,
            )
        )

    for consumable in consumables:
        consumable.save()

    bag.was_delivered = True
    bag.save()


@task(bind=False, priority=TaskPriority.WEB_SERVICE_PAYMENT.value)
def refund_mentoring_session(session_id: int, **_: Any):
    from breathecode.mentorship.models import MentorshipSession

    logger.info(f"Starting refund_mentoring_session for mentoring session {session_id}")

    if not (
        mentorship_session := MentorshipSession.objects.filter(
            id=session_id, mentee__isnull=False, service__isnull=False, status__in=["FAILED", "IGNORED"]
        ).first()
    ):
        raise AbortTask(f"MentoringSession with id {session_id} not found or is invalid")

    mentee = mentorship_session.mentee
    service = mentorship_session.service

    consumption_session = (
        ConsumptionSession.objects.filter(
            consumable__user=mentee, consumable__mentorship_service_set__mentorship_services=service
        )
        .exclude(status="CANCELLED")
        .first()
    )

    if not consumption_session:
        raise AbortTask(f"ConsumptionSession not found for mentorship session {session_id}")

    if consumption_session.status == "CANCELLED":
        raise AbortTask(f"ConsumptionSession already cancelled for mentorship session {session_id}")

    if consumption_session.status == "DONE":
        logger.info("Refunding consumption session because it was discounted")

        how_many = consumption_session.how_many
        consumable = consumption_session.consumable
        reimburse_service_units.send_robust(instance=consumable, sender=consumable.__class__, how_many=how_many)

    consumption_session.status = "CANCELLED"
    consumption_session.save()


@task(bind=False, priority=TaskPriority.ACADEMY.value)
def add_cohort_set_to_subscription(subscription_id: int, cohort_set_id: int, **_: Any):
    logger.info(
        f"Starting add_cohort_set_to_subscription for subscription {subscription_id} cohort_set {cohort_set_id}"
    )

    subscription = (
        Subscription.objects.filter(id=subscription_id).exclude(status__in=["CANCELLED", "DEPRECATED"]).first()
    )

    if not subscription:
        raise RetryTask(f"Subscription with id {subscription_id} not found")

    if subscription.valid_until and subscription.valid_until < timezone.now():
        raise AbortTask(f"The subscription {subscription.id} is over")

    if subscription.selected_cohort_set:
        raise AbortTask(f"Subscription with id {subscription_id} already have a cohort set")

    cohort_set = CohortSet.objects.filter(id=cohort_set_id).first()
    if not cohort_set:
        raise RetryTask(f"CohortSet with id {cohort_set_id} not found")

    subscription.selected_cohort_set = cohort_set
    subscription.save()


@task(bind=False, priority=TaskPriority.WEB_SERVICE_PAYMENT.value)
def update_subscription_service_stock_schedulers(plan_id: int, subscription_id: int, **_: Any):
    plan = Plan.objects.filter(id=plan_id).only("id").prefetch_related("service_items").first()
    subscription = Subscription.objects.filter(plans__id=subscription_id).only("id", "next_payment_at").first()

    for plan_service_item in PlanServiceItem.objects.filter(plan=plan).prefetch_related("service_item"):
        service_item = plan_service_item.service_item
        scheduler = ServiceStockScheduler.objects.filter(
            plan_handler__subscription__id=subscription_id,
            plan_handler__handler__plan=plan,
            plan_handler__handler__service_item__id=service_item.id,
        ).first()

        if not scheduler:
            unit = service_item.renew_at
            unit_type = service_item.renew_at_unit
            delta = actions.calculate_relative_delta(unit, unit_type)
            valid_until = subscription.next_payment_at + delta

            if valid_until > subscription.next_payment_at:
                valid_until = subscription.next_payment_at

            if subscription.valid_until and valid_until > subscription.valid_until:
                valid_until = subscription.valid_until

            handler, _ = PlanServiceItemHandler.objects.get_or_create(
                subscription=subscription, handler=plan_service_item
            )

            ServiceStockScheduler.objects.get_or_create(plan_handler=handler)


@task(bind=False, priority=TaskPriority.WEB_SERVICE_PAYMENT.value)
def update_plan_financing_service_stock_schedulers(plan_id: int, subscription_id: int, **_: Any):
    plan = Plan.objects.filter(id=plan_id).only("id").prefetch_related("service_items").first()
    plan_financing = PlanFinancing.objects.filter(plans__id=subscription_id).only("id", "next_payment_at").first()

    for plan_service_item in PlanServiceItem.objects.filter(plan=plan).prefetch_related("service_item"):
        service_item = plan_service_item.service_item
        scheduler = ServiceStockScheduler.objects.filter(
            plan_handler__plan_financing__id=subscription_id,
            plan_handler__handler__plan=plan,
            plan_handler__handler__service_item__id=service_item.id,
        ).first()

        if not scheduler:
            unit = service_item.renew_at
            unit_type = service_item.renew_at_unit
            delta = actions.calculate_relative_delta(unit, unit_type)
            valid_until = plan_financing.next_payment_at + delta

            if valid_until > plan_financing.next_payment_at:
                valid_until = plan_financing.next_payment_at

            if plan_financing.valid_until and valid_until > plan_financing.valid_until:
                valid_until = plan_financing.valid_until

            handler, _ = PlanServiceItemHandler.objects.get_or_create(
                plan_financing=plan_financing, handler=plan_service_item
            )

            ServiceStockScheduler.objects.get_or_create(plan_handler=handler)


@task(bind=False, priority=TaskPriority.WEB_SERVICE_PAYMENT.value)
def update_service_stock_schedulers(plan_id: int, **_: Any):
    for subscription in Subscription.objects.filter(plans__id=plan_id).only("id"):
        update_subscription_service_stock_schedulers.delay(plan_id, subscription.id)

    for plan_financing in PlanFinancing.objects.filter(plans__id=plan_id).only("id"):
        update_plan_financing_service_stock_schedulers.delay(plan_id, plan_financing.id)


@task(bind=False, priority=TaskPriority.WEB_SERVICE_PAYMENT.value)
def set_proof_of_payment_confirmation_url(file_id: int, proof_of_payment_id: int, **_: Any):
    from breathecode.media.settings import transfer

    file = File.objects.filter(id=file_id, status=File.Status.TRANSFERRING).first()
    if not file:
        raise RetryTask(f"File with id {file_id} not found or is not transferring")

    proof = ProofOfPayment.objects.filter(id=proof_of_payment_id).first()
    if not proof:
        raise RetryTask(f"Proof of Payment with id {proof_of_payment_id} not found")

    url = transfer(file, os.getenv("PROOF_OF_PAYMENT_BUCKET"))

    proof.confirmation_image_url = url
    proof.status = ProofOfPayment.Status.DONE
    proof.save()


@task(bind=False, priority=TaskPriority.WEB_SERVICE_PAYMENT.value)
def process_google_webhook(hook_id: int, **_: Any):
    from breathecode.authenticate.models import CredentialsGoogle, GoogleWebhook

    logger.info(f"Starting process_google_webhook for id {hook_id}")

    hook = GoogleWebhook.objects.filter(id=hook_id).first()
    if not hook:
        raise RetryTask(f"GoogleWebhook with id {hook_id} not found")

    if hook.status == GoogleWebhook.Status.DONE:
        raise AbortTask(f"GoogleWebhook with id {hook_id} was processed")

    users_ids = AcademyAuthSettings.objects.filter(google_cloud_owner__isnull=False).values_list(
        "google_cloud_owner_id", flat=True
    )

    credentials = CredentialsGoogle.objects.filter(user__id__in=users_ids).only("token", "refresh_token")
    if credentials.exists() is False:
        raise AbortTask("CredentialsGoogle not found")

    google = Google()
    google.run_webhook(hook, credentials)


@task(bind=True, priority=TaskPriority.WEB_SERVICE_PAYMENT.value)
def retry_pending_bag_delivery(self, bag_id: int, **_: Any):
    """
    Task to retry the delivery of a bag that was paid but not delivered.
    This task will attempt to create a subscription or plan financing based on the bag's configuration.
    It will retry twice with a delay between attempts.
    """
    logger.info(f"Starting retry_pending_bag_delivery for bag {bag_id}")

    if not (bag := Bag.objects.filter(id=bag_id, status="PAID", was_delivered=False).first()):
        logger.info(f"Bag with id {bag_id} not found or already delivered")
        return

    # Get the latest fulfilled invoice for this bag
    invoice = Invoice.objects.filter(bag=bag, status="FULFILLED").order_by("-paid_at").first()

    if not invoice:
        logger.error(f"No fulfilled invoice found for bag {bag_id}")
        return

    # Determine if this is a free subscription
    is_free = invoice.amount == 0

    # Determine if this is a plan financing or a subscription
    if bag.how_many_installments > 1:
        # This is a plan financing
        logger.info(f"Attempting to build plan financing for bag {bag_id}")
        build_plan_financing.delay(bag_id=bag.id, invoice_id=invoice.id, is_free=is_free)
    elif is_free:
        # This is a free subscription
        logger.info(f"Attempting to build free subscription for bag {bag_id}")
        build_free_subscription.delay(bag_id=bag.id, invoice_id=invoice.id)
    else:
        # This is a regular subscription
        logger.info(f"Attempting to build subscription for bag {bag_id}")
        build_subscription.delay(bag_id=bag.id, invoice_id=invoice.id)

    # Schedule a second attempt after 30 minutes if the bag is still not delivered
    self.apply_async(
        kwargs={"bag_id": bag_id},
        countdown=1800,  # 30 minutes in seconds
    )


@task(bind=False, priority=TaskPriority.WEB_SERVICE_PAYMENT.value)
def check_and_retry_pending_bags(**_: Any):
    """
    Task to check for bags that are paid but not delivered and retry their delivery.
    This task is meant to be scheduled periodically.
    """
    logger.info("Starting check_and_retry_pending_bags")

    # Find bags that are paid but not delivered for more than 1 hour
    utc_now = timezone.now()
    pending_bags = Bag.objects.filter(status="PAID", was_delivered=False, updated_at__lte=utc_now - timedelta(hours=1))

    count = pending_bags.count()
    logger.info(f"Found {count} pending bags to be delivered")

    # Schedule retry for each pending bag
    for bag in pending_bags:
        retry_pending_bag_delivery.delay(bag_id=bag.id)

    return count


@task(bind=False, priority=TaskPriority.NOTIFICATION.value)
def process_auto_recharge(
    consumable_id: int,
    **_: Any,
):
    """
    Process automatic consumable recharge for a billing team.

    This task:
    1. Acquires Redis lock to prevent concurrent recharges
    2. Creates consumables for team-allowed services
    3. Charges the subscription owner via Stripe
    4. Tracks spending via invoices

    Args:
        team_id: SubscriptionBillingTeam ID
        recharge_amount: Amount in subscription currency to recharge
        seat_id: Optional SubscriptionSeat ID for per-seat recharge
        service_id: Optional Service ID to restrict the recharge to a single service

    Note:
        Uses Redis lock to prevent race conditions when multiple
        consumptions trigger recharge simultaneously.
    """

    try:
        consumable = Consumable.objects.select_related("subscription").get(id=consumable_id)
    except Consumable.DoesNotExist:
        raise AbortTask(f"Consumable {consumable_id} not found")

    actions.process_auto_recharge(consumable)


@task(bind=False, priority=TaskPriority.NOTIFICATION.value)
def send_coinbase_error_email(
    invoice_id: int,
    error_type: str,
    error_summary: str,
    **_: Any,
):
    """
    Send email to user when there's an error processing their Coinbase payment.
    Uses Redis lock to ensure only ONE email is sent even if webhook retries.

    Args:
        invoice_id: Invoice ID
        error_type: Type of error ("processing_error", "failed_payment", etc)
        error_summary: Brief description of the error
    """
    try:
        invoice = (
            Invoice.objects.select_related("bag", "academy", "user")
            .prefetch_related("bag__plans")
            .filter(id=invoice_id)
            .first()
        )

        if not invoice:
            raise AbortTask(f"Invoice {invoice_id} not found")

        user = invoice.user
        plan = invoice.bag.plans.first() if invoice.bag else None
        plan_title = plan.title or plan.slug if plan else "your plan"
        support_email = invoice.academy.feedback_email if invoice.academy else "support@4geeks.com"

        # Get user language
        from breathecode.authenticate.models import UserSetting

        user_setting = UserSetting.objects.filter(user=user).first()
        lang = user_setting.lang if user_setting and user_setting.lang else "en"

        lock_key = f"payment_error_email:{invoice_id}:{error_type}"

        client = None
        if IS_DJANGO_REDIS:
            client = get_redis_connection("default")

        try:
            with Lock(client, lock_key, timeout=300, blocking_timeout=300):
                # Check if email was already sent
                sent_key = f"payment_error_email_sent:{invoice_id}"
                if cache.get(sent_key):
                    logger.info(f"send_coinbase_error_email: Email already sent for invoice_id={invoice_id}, skipping")
                    return

                # Messages in English and Spanish
                messages = {
                    "en": {
                        "subject": f"Payment Processing Issue - {plan_title}",
                        "message": f"Hello {user.first_name or 'there'},<br><br>"
                        f"We encountered a technical issue while processing your {plan_title} payment "
                        f"(Invoice ID: {invoice_id}).<br><br>"
                        f"Please contact our support team at <a href='mailto:{support_email}'>{support_email}</a> "
                        f"so we can help you resolve this quickly.<br><br>"
                        f"We apologize for any inconvenience.",
                    },
                    "es": {
                        "subject": f"Problema Procesando tu Pago - {plan_title}",
                        "message": f"Hola {user.first_name or ''},<br><br>"
                        f"Encontramos un problema técnico al procesar el pago de {plan_title} "
                        f"(ID de Invoice: {invoice_id}).<br><br>"
                        f"Por favor contacta a nuestro equipo de soporte en <a href='mailto:{support_email}'>{support_email}</a> "
                        f"para que podamos ayudarte a resolver esto rápidamente.<br><br>"
                        f"Disculpa las molestias.",
                    },
                }

                selected_lang = lang if lang in messages else "en"

                context = {
                    "SUBJECT": messages[selected_lang]["subject"],
                    "MESSAGE": messages[selected_lang]["message"],
                }

                # Use "message" template
                notify_actions.send_email_message(
                    "message",
                    user.email,
                    context,
                    academy=invoice.academy,
                )

                # Mark as sent in cache (24 hour expiry)
                cache.set(sent_key, True, 86400)  # 24 hours

                logger.info(
                    f"send_coinbase_error_email: Email sent successfully - "
                    f"invoice_id={invoice_id}, error_type={error_type}"
                )

        except LockError:
            # Another worker is already sending the email
            logger.info(
                f"send_coinbase_error_email: Email already being sent by another worker - "
                f"invoice_id={invoice_id}, error_type={error_type}"
            )

    except Exception as e:
        logger.error(
            f"send_coinbase_error_email: Failed to send email - "
            f"invoice_id={invoice_id}, error_type={error_type}, error={str(e)}",
            exc_info=True,
        )
        # Don't raise - email failures shouldn't break the flow


@task(bind=False, priority=TaskPriority.NOTIFICATION.value)
def send_checkout_fulfillment_error_email(
    bag_id: int,
    session_id: str,
    error_summary: str,
    **_: Any,
):
    """
    Notify the user when Stripe Checkout payment succeeded but fulfillment failed.
    Uses Redis lock to ensure only one email per checkout session.
    """
    try:
        bag = Bag.objects.select_related("user", "academy").prefetch_related("plans").filter(id=bag_id).first()
        if not bag:
            raise AbortTask(f"Bag {bag_id} not found")

        user = bag.user
        plan = bag.plans.first()
        plan_title = plan.title or plan.slug if plan else "your plan"
        support_email = bag.academy.feedback_email if bag.academy else "support@4geeks.com"

        user_settings = get_user_settings(user.id)
        lang = user_settings.lang if user_settings and user_settings.lang else "en"

        lock_key = f"checkout_fulfillment_error_email:{session_id}"

        client = None
        if IS_DJANGO_REDIS:
            client = get_redis_connection("default")

        try:
            with Lock(client, lock_key, timeout=300, blocking_timeout=300):
                sent_key = f"checkout_fulfillment_error_email_sent:{session_id}"
                if cache.get(sent_key):
                    logger.info(
                        "send_checkout_fulfillment_error_email: already sent for session_id=%s, skipping",
                        session_id,
                    )
                    return

                messages = {
                    "en": {
                        "subject": f"Payment Processing Issue - {plan_title}",
                        "message": f"Hello {user.first_name or 'there'},<br><br>"
                        f"We encountered a technical issue while activating "
                        f"your {plan_title} purchase (reference: {session_id}).<br><br>"
                        f"Please contact our support team at <a href='mailto:{support_email}'>{support_email}</a> "
                        f"so we can help you resolve this quickly.<br><br>",
                    },
                    "es": {
                        "subject": f"Problema Procesando tu Pago - {plan_title}",
                        "message": f"Hola {user.first_name or ''},<br><br>"
                        f"Recibimos tu pago pero encontramos un problema técnico al activar "
                        f"tu compra de {plan_title} (referencia: {session_id}).<br><br>"
                        f"Por favor contacta a nuestro equipo de soporte en <a href='mailto:{support_email}'>{support_email}</a> "
                        f"para que podamos ayudarte a resolver esto rápidamente.<br><br>",
                    },
                }

                selected_lang = lang if lang in messages else "en"

                notify_actions.send_email_message(
                    "message",
                    user.email,
                    {
                        "SUBJECT": messages[selected_lang]["subject"],
                        "MESSAGE": messages[selected_lang]["message"],
                    },
                    academy=bag.academy,
                )

                cache.set(sent_key, True, 86400)

                logger.info(
                    "send_checkout_fulfillment_error_email: sent bag_id=%s session_id=%s summary=%s",
                    bag_id,
                    session_id,
                    error_summary[:80],
                )

        except LockError:
            logger.info(
                "send_checkout_fulfillment_error_email: lock held for session_id=%s, skipping duplicate",
                session_id,
            )

    except Exception as e:
        logger.error(
            "send_checkout_fulfillment_error_email: failed bag_id=%s session_id=%s error=%s",
            bag_id,
            session_id,
            str(e),
            exc_info=True,
        )
