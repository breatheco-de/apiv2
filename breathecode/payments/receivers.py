import logging
from typing import Type

from django.contrib.auth.models import Group, User
from django.db import transaction
from django.db.models import Q
from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver
from django.utils import timezone
from task_manager.django.actions import schedule_task

import breathecode.authenticate.tasks as auth_tasks
import breathecode.activity.tasks as tasks_activity
from breathecode.authenticate.actions import get_user_settings, revoke_user_discord_permissions
from breathecode.authenticate.models import Cohort, CredentialsDiscord, GoogleWebhook, UserInvite
from breathecode.authenticate.signals import google_webhook_saved, invite_status_updated
from breathecode.commission.tasks import register_referral_from_invoice
from breathecode.mentorship.models import MentorshipSession
from breathecode.mentorship.signals import mentorship_session_status
from breathecode.monitoring import signals as monitoring_signals
from breathecode.monitoring.models import StripeEvent
from breathecode.payments import actions, tasks

from .actions import validate_auto_recharge_service_units
from .models import (
    Bag,
    Consumable,
    Invoice,
    PaymentMethod,
    Plan,
    PlanFinancing,
    PlanFinancingTeam,
    Subscription,
    SubscriptionBillingTeam,
    SubscriptionSeat,
)
from .signals import (
    consume_service,
    grant_plan_permissions,
    grant_service_permissions,
    lose_service_permissions,
    reimburse_service_units,
    revoke_plan_permissions,
    update_plan_m2m_service_items,
)

logger = logging.getLogger(__name__)


@receiver(consume_service, sender=Consumable)
def consume_service_receiver(sender: Type[Consumable], instance: Consumable, how_many: float, **kwargs):
    if instance.how_many == 0:
        lose_service_permissions.send_robust(instance=instance, sender=sender)
        return

    if instance.how_many == -1:
        return

    instance.how_many -= how_many
    instance.save()

    if instance.how_many == 0:
        lose_service_permissions.send_robust(instance=instance, sender=sender)


@receiver(reimburse_service_units, sender=Consumable)
def reimburse_service_units_receiver(sender: Type[Consumable], instance: Consumable, how_many: float, **kwargs):
    if instance.how_many == -1:
        return

    grant_permissions = not instance.how_many and how_many

    instance.how_many += how_many
    instance.save()

    if grant_permissions:
        grant_service_permissions.send_robust(instance=instance, sender=sender)


@receiver(lose_service_permissions, sender=Consumable)
def lose_service_permissions_receiver(sender: Type[Consumable], instance: Consumable, **kwargs):
    now = timezone.now()

    if instance.how_many != 0:
        return

    user = instance.subscription_seat.user if instance.subscription_seat else instance.user
    subscription_team = instance.subscription_billing_team or (
        instance.subscription_seat.billing_team if instance.subscription_seat else None
    )

    # Build base filter: user and seat consumables
    if subscription_team:
        # limit to consumables linked to the same billing team
        base_filter = Q(user=user, subscription_billing_team=subscription_team) | Q(
            subscription_seat__user=user, subscription_seat__billing_team=subscription_team
        )
    else:
        base_filter = Q(user=user) | Q(subscription_seat__user=user)

    # Include team-shared consumables only if strategy is PER_TEAM
    team_shared_filter = Q()
    if (
        subscription_team
        and subscription_team.consumption_strategy == SubscriptionBillingTeam.ConsumptionStrategy.PER_TEAM
    ):
        team_shared_filter = Q(
            user__isnull=True,
            subscription_billing_team__isnull=False,
            subscription_billing_team=subscription_team,
        )

    consumables = Consumable.objects.filter(
        Q(valid_until__lte=now) | Q(valid_until=None),
        base_filter | team_shared_filter,
    ).exclude(how_many=0)

    # for group in instance.user.groups.all():
    for group in instance.service_item.service.groups.all():

        how_many = consumables.filter(service_item__service__groups__name=group.name).distinct().count()
        if how_many == 0:
            user.groups.remove(group)


def grant_service_permissions_receiver(sender: Type[Consumable], instance: Consumable, **kwargs):
    # Only grant when this consumable has units available now (> 0). Infinite (-1) is handled elsewhere.
    if instance.how_many <= 0:
        return

    # Determine the affected user and billing team context
    user = instance.subscription_seat.user if instance.subscription_seat else instance.user
    subscription_team = instance.subscription_billing_team or (
        instance.subscription_seat.billing_team if instance.subscription_seat else None
    )

    groups = instance.service_item.service.groups.all()

    def grant_for_user(target_user):
        for group in groups:
            if not target_user.groups.filter(name=group.name).exists():
                target_user.groups.add(group)

    if not user and subscription_team:
        # Grant to all users in the team only if the consumption strategy is PER_TEAM
        if subscription_team.consumption_strategy == SubscriptionBillingTeam.ConsumptionStrategy.PER_TEAM:
            seats = SubscriptionSeat.objects.filter(billing_team=subscription_team, user__isnull=False).select_related(
                "user"
            )
            for seat in seats:
                grant_for_user(seat.user)
        return

    if user:
        grant_for_user(user)


grant_service_permissions.connect(grant_service_permissions_receiver, sender=Consumable)


def grant_plan_permissions_receiver(
    sender: Type[Subscription] | Type[PlanFinancing], instance: Subscription | PlanFinancing, **kwargs
):
    """
    Add the user to the Paid Student group when a subscription/plan financing is created
    or when its status changes to ACTIVE. The signal is only emitted for paid plans.
    """

    def grant(user: User):
        nonlocal group
        if group and not user.groups.filter(name="Paid Student").exists():
            user.groups.add(group)

    group = Group.objects.filter(name="Paid Student").first()
    if isinstance(instance, Subscription) and (
        team := SubscriptionBillingTeam.objects.filter(subscription=instance).first()
    ):
        for seat in team.subscription_seat_set.all():
            grant(seat.user)
    else:
        grant(instance.user)


grant_plan_permissions.connect(grant_plan_permissions_receiver, sender=Subscription)
grant_plan_permissions.connect(grant_plan_permissions_receiver, sender=PlanFinancing)


def revoke_plan_permissions_receiver(sender, instance, **kwargs):
    """
    Remove the user from the Paid Student group only if the user has
    NO other active PAID subscriptions or plan financings.
    """

    from .actions import user_has_active_paid_plans

    group = Group.objects.filter(name="Paid Student").first()

    def revoke(user: User):
        nonlocal group
        user = instance.user

        if not group or not user.groups.filter(name="Paid Student").exists():
            return

        if not user_has_active_paid_plans(user):
            user.groups.remove(group)

    if isinstance(instance, Subscription) and (
        team := SubscriptionBillingTeam.objects.filter(subscription=instance).first()
    ):
        for seat in team.subscription_seat_set.all():
            revoke(seat.user)
    else:
        revoke(instance.user)


revoke_plan_permissions.connect(revoke_plan_permissions_receiver, sender=Subscription)
revoke_plan_permissions.connect(revoke_plan_permissions_receiver, sender=PlanFinancing)


def handle_seat_invite_accepted(sender: Type[UserInvite], instance: UserInvite, **kwargs):
    """When an invite is accepted, bind pending SubscriptionSeat by email and issue consumables."""
    if instance.status != "ACCEPTED" or not instance.user_id:
        return

    if instance.plan_financing_seat_id:
        seat = instance.plan_financing_seat
        team = seat.team
        financing = team.financing

        seat.user = instance.user
        seat.email = instance.user.email.lower()
        seat.save(update_fields=["user", "email"])

        logger.info(
            "Activated plan financing seat via invite: financing=%s user=%s",
            financing.id,
            instance.user_id,
        )

        per_team_strategy = team and team.consumption_strategy == PlanFinancingTeam.ConsumptionStrategy.PER_TEAM

        if not per_team_strategy:
            Consumable.objects.filter(plan_financing_seat=seat, user__isnull=True).update(user=instance.user)

        for plan in financing.plans.all():
            selected_cohort = instance.cohort.slug if instance.cohort_id else None
            actions.grant_student_capabilities(instance.user, plan, selected_cohort=selected_cohort)

        tasks.build_service_stock_scheduler_from_plan_financing.delay(financing.id, seat_id=seat.id)
        return

    seats = SubscriptionSeat.objects.filter(email__iexact=instance.email.strip(), user__isnull=True)
    for seat in seats.select_related("billing_team", "billing_team__subscription"):
        subscription = seat.billing_team.subscription

        # Bind seat to user and normalize email
        seat.user = instance.user
        seat.email = instance.user.email.lower()
        seat.save()

        logger.info(
            "Activated team seat via invite: subscription=%s user=%s",
            subscription.id,
            instance.user_id,
        )

        # Determine effective strategy
        team = seat.billing_team
        plan = subscription.plans.first()
        plan_strategy = getattr(plan, "consumption_strategy", Plan.ConsumptionStrategy.PER_SEAT)
        per_seat_enabled = team and (
            team.consumption_strategy == SubscriptionBillingTeam.ConsumptionStrategy.PER_SEAT
            or plan_strategy == Plan.ConsumptionStrategy.BOTH
        )

        # Assign existing consumables that were created with user=None to the newly accepted user
        if per_seat_enabled:
            # Update existing consumables for this seat to assign them to the user
            Consumable.objects.filter(subscription_seat=seat, user__isnull=True).update(user=instance.user)

            # Grant student capabilities for each plan
            selected_cohort = instance.cohort.slug if instance.cohort_id else None
            for p in subscription.plans.all():
                actions.grant_student_capabilities(instance.user, p, selected_cohort=selected_cohort)


# to be able to use unittest instead of integration test
invite_status_updated.connect(handle_seat_invite_accepted, sender=UserInvite)


@receiver(revoke_plan_permissions, sender=Subscription)
@receiver(revoke_plan_permissions, sender=PlanFinancing)
def revoke_discord_permissions_receiver(sender, instance, **kwargs):
    """
    Remove the user from the Discord server only if the user has
    NO other active 4Geeks Plus PAID subscriptions or plan financings.
    """

    def schedule_delayed_revoke(date_field, date_value):
        if date_value and date_value >= timezone.now():
            days_until = int((date_value - timezone.now()).total_seconds() / (24 * 60 * 60)) + 1
            entity_type = "subscription" if isinstance(instance, Subscription) else "plan_financing"
            manager = schedule_task(auth_tasks.delayed_revoke_discord_permissions, f"{days_until}d")
            if not manager.exists(instance.id, entity_type, date_field):
                manager.call(instance.id, entity_type, date_field)
            return True
        return False

    from .actions import user_has_active_4geeks_plus_plans

    if user_has_active_4geeks_plus_plans(instance.user):
        logger.info(f"User {instance.user.id} still has active paid plans, skipping Discord permissions revoke")
        return
    entity_type = "subscription" if isinstance(instance, Subscription) else "plan_financing"
    if entity_type == "subscription":
        plan_slug = Plan.objects.filter(subscription=instance).first().slug
    else:
        plan_slug = Plan.objects.filter(planfinancing=instance).first().slug
    if plan_slug == "4geeks-plus-subscription" or plan_slug == "4geeks-plus-planfinancing":
        if instance.status == "CANCELLED":
            if instance.valid_until:
                if instance.valid_until >= timezone.now():
                    logger.debug(
                        "The user still has time to pay the subscription after being cancelled, scheduling Discord revoke"
                    )
                    schedule_delayed_revoke("valid_until", instance.valid_until)
                    return
                else:
                    revoke_user_discord_permissions(instance.user, instance.academy)
                    return

            if instance.next_payment_at:
                if instance.next_payment_at >= timezone.now():
                    logger.debug(
                        "The user still has time to pay the subscription after being cancelled, scheduling Discord revoke"
                    )
                    schedule_delayed_revoke("next_payment_at", instance.next_payment_at)
                    return
                else:
                    revoke_user_discord_permissions(instance.user, instance.academy)
                    return
        else:

            if instance.valid_until:
                if instance.valid_until >= timezone.now():

                    logger.debug("The user still has time to pay the subscription, scheduling Discord revoke")
                    schedule_delayed_revoke("valid_until", instance.valid_until)
                    return
                else:

                    revoke_user_discord_permissions(instance.user, instance.academy)
                    return
            else:
                revoke_user_discord_permissions(instance.user, instance.academy)
                return


@receiver(grant_plan_permissions, sender=Subscription)
@receiver(grant_plan_permissions, sender=PlanFinancing)
def grant_discord_permissions_receiver(sender, instance, **kwargs):
    discord_creds = CredentialsDiscord.objects.filter(user=instance.user).first()
    if not discord_creds:
        logger.debug(f"User {instance.user.id} has no Discord credentials, skipping grant")
        return False
    cohort_academy = Cohort.objects.filter(academy=instance.academy).prefetch_related("academy").first()
    if not cohort_academy:
        return False
    cohorts = Cohort.objects.filter(cohortuser__user=instance.user, academy=cohort_academy.academy.id).all()

    plan_slug = Plan.objects.filter(subscription=instance).first().slug
    if plan_slug == "4geeks-plus-subscription" or plan_slug == "4geeks-plus-planfinancing":
        for cohort in cohorts:
            if cohort.shortcuts:
                for shortcut in cohort.shortcuts:
                    if shortcut.get("label", None) != "Discord":
                        continue

                    try:
                        auth_tasks.assign_discord_role_task.delay(
                            shortcut.get("server_id", None),
                            int(discord_creds.discord_id),
                            shortcut.get("role_id", None),
                            cohort_academy.academy.id,
                        )
                    except Exception as e:
                        logger.error(str(e))


@receiver(mentorship_session_status, sender=MentorshipSession)
def post_mentoring_session_ended(sender: Type[MentorshipSession], instance: MentorshipSession, **kwargs):
    if instance.mentee and instance.service and instance.status in ["FAILED", "IGNORED"]:
        tasks.refund_mentoring_session.delay(instance.id)


@receiver(m2m_changed, sender=Plan.service_items.through)
def plan_m2m_wrapper(sender, instance: Plan, **kwargs):
    if kwargs["action"] != "post_add":
        return

    update_plan_m2m_service_items.send_robust(sender=sender, instance=instance)


@receiver(update_plan_m2m_service_items, sender=Plan.service_items.through)
def plan_m2m_changed(sender, instance: Plan, **kwargs):
    tasks.update_service_stock_schedulers.delay(instance.id)


@receiver(google_webhook_saved, sender=GoogleWebhook)
def process_google_webhook_on_created(sender: Type[GoogleWebhook], instance: GoogleWebhook, created: bool, **kwargs):
    if created:
        tasks.process_google_webhook.delay(instance.id)


def check_consumable_balance_for_auto_recharge(sender: Type[Consumable], instance: Consumable, **kwargs):
    """
    Monitor consumable consumption and trigger auto-recharge when balance is low.

    This receiver checks if:
    1. The consumable belongs to a billing team with auto-recharge enabled
    2. The current balance (in subscription currency) falls below the threshold
    3. Monthly spending limit hasn't been exceeded

    If all conditions are met, it triggers a recharge via signal.
    """

    price, amount, error = validate_auto_recharge_service_units(instance)
    if error:
        logger.warning(f"Auto-recharge not allowed for consumable {instance.id}: {error}")
        return

    if amount <= 0:
        logger.warning(f"Auto-recharge not allowed for consumable {instance.id}: amount is zero or negative")
        return

    tasks.process_auto_recharge.delay(instance.id)


post_save.connect(check_consumable_balance_for_auto_recharge, sender=Consumable)


def _load_stripe_checkout_fulfillment_context(
    session: dict, *, require_subscription: bool = False, require_plan_financing: bool = False
) -> tuple[dict | None, str | None]:
    """
    Parse checkout session metadata and load related models in one pass.

    Returns (context, error). context is None without error when required metadata is missing.
    """

    metadata = session.get("metadata") or {}
    if not metadata.get("bag_id"):
        return None, None
    if require_subscription and not metadata.get("subscription_id"):
        return None, None
    if require_plan_financing and not metadata.get("plan_financing_id"):
        return None, None

    session_id = session.get("id")
    if not session_id:
        return None, "Missing checkout session id"

    try:
        bag_id = int(float(metadata["bag_id"]))
        amount = float(metadata["amount"])
        original_price = float(metadata["original_price"])
        subscription_id = int(float(metadata["subscription_id"])) if require_subscription else None
        plan_financing_id = int(float(metadata["plan_financing_id"])) if require_plan_financing else None
    except KeyError as exc:
        return None, f"Missing metadata field: {exc.args[0]}"
    except (TypeError, ValueError):
        if require_subscription or require_plan_financing:
            return None, "Invalid bag_id, renewal id, amount, or original_price in metadata"
        return None, "Invalid bag_id, amount, or original_price in metadata"

    bag = Bag.objects.filter(id=bag_id).select_related("user", "academy", "currency").first()
    if not bag:
        return None, f"Bag {bag_id} not found"

    subscription = None
    plan_financing = None
    if require_subscription:
        subscription = Subscription.objects.filter(id=subscription_id, user=bag.user).first()
        if not subscription:
            return None, f"Subscription {subscription_id} not found"
    if require_plan_financing:
        plan_financing = PlanFinancing.objects.filter(id=plan_financing_id, user=bag.user).first()
        if not plan_financing:
            return None, f"PlanFinancing {plan_financing_id} not found"

    payment_method = None
    if payment_method_id := metadata.get("payment_method_id"):
        try:
            payment_method = PaymentMethod.objects.filter(id=int(float(payment_method_id))).first()
        except (TypeError, ValueError):
            pass

    chosen_period = metadata.get("chosen_period") or None
    if chosen_period and chosen_period not in {value for value, _ in Bag.ChosenPeriod.choices}:
        chosen_period = None

    user_settings = get_user_settings(bag.user.id)
    lang = user_settings.lang if user_settings and user_settings.lang else "en"

    ctx = {
        "session_id": session_id,
        "bag": bag,
        "amount": amount,
        "original_price": original_price,
        "payment_method": payment_method,
        "chosen_period": chosen_period,
        "lang": lang,
    }

    if require_subscription:
        ctx["subscription"] = subscription
    elif require_plan_financing:
        ctx["plan_financing"] = plan_financing
    else:
        how_many_installments = 0
        if raw_installments := metadata.get("how_many_installments"):
            try:
                how_many_installments = int(float(raw_installments))
            except (TypeError, ValueError):
                pass
        financing_option_id = None
        if raw_financing_option_id := metadata.get("financing_option_id"):
            try:
                financing_option_id = int(float(raw_financing_option_id))
            except (TypeError, ValueError):
                pass
        ctx["how_many_installments"] = how_many_installments
        ctx["financing_option_id"] = financing_option_id
        ctx["selected_cohort"] = metadata.get("selected_cohort") or None

    return ctx, None


@receiver(monitoring_signals.stripe_webhook, sender=StripeEvent)
def stripe_checkout_payment_fulfillment(sender: Type[StripeEvent], instance: StripeEvent, **kwargs):
    handler_key = "payments.stripe_checkout_payment_fulfillment"

    if instance.type not in (
        "checkout.session.completed",
        "checkout.session.async_payment_succeeded",
        "checkout.session.async_payment_failed",
    ):
        return

    session = instance.data.get("object") or instance.data
    metadata = session.get("metadata") or {}
    if not metadata.get("bag_id"):
        return

    if metadata.get("subscription_id") or metadata.get("plan_financing_id"):
        return

    if instance.type == "checkout.session.async_payment_failed":
        instance.status_texts[handler_key] = "async payment failed"
        instance.status = "ERROR"
        instance.save()
        return

    payment_status = session.get("payment_status")
    if instance.type == "checkout.session.completed" and payment_status == "unpaid":
        instance.status_texts.pop(handler_key, None)
        instance.status = "DONE" if len(instance.status_texts) == 0 else "ERROR"
        instance.save()
        return

    if payment_status != "paid":
        return

    ctx, error = _load_stripe_checkout_fulfillment_context(session)
    if error:
        instance.status_texts[handler_key] = error
        instance.status = "ERROR"
        instance.save()
        if metadata.get("bag_id") and session.get("id"):
            tasks.send_checkout_fulfillment_error_email.delay(
                int(float(metadata["bag_id"])),
                session["id"],
                error[:200],
            )
        return
    if not ctx:
        return

    session_id = ctx["session_id"]
    bag = ctx["bag"]
    amount = ctx["amount"]
    original_price = ctx["original_price"]
    payment_method = ctx["payment_method"]
    how_many_installments = ctx["how_many_installments"]
    financing_option_id = ctx["financing_option_id"]
    chosen_period = ctx["chosen_period"]
    selected_cohort = ctx["selected_cohort"]
    lang = ctx["lang"]

    if Invoice.objects.filter(stripe_id=session_id, status=Invoice.Status.FULFILLED).exists():
        instance.status_texts.pop(handler_key, None)
        instance.status = "DONE" if len(instance.status_texts) == 0 else "ERROR"
        instance.save()
        return

    utc_now = timezone.now()

    try:
        with transaction.atomic():
            sid = transaction.savepoint()

            invoice, created = Invoice.objects.get_or_create(
                stripe_id=session_id,
                defaults={
                    "bag": bag,
                    "user": bag.user,
                    "amount": amount,
                    "currency": bag.currency,
                    "status": Invoice.Status.FULFILLED,
                    "externally_managed": True,
                    "academy": bag.academy,
                    "paid_at": utc_now,
                    "payment_method": payment_method,
                },
            )

            if not created and invoice.status == Invoice.Status.FULFILLED:
                transaction.savepoint_rollback(sid)
                instance.status_texts.pop(handler_key, None)
                instance.status = "DONE" if len(instance.status_texts) == 0 else "ERROR"
                instance.save()
                return

            invoice.refresh_from_db()

            bag.status = "PAID"
            bag.chosen_period = chosen_period or "NO_SET"
            bag.how_many_installments = how_many_installments
            bag.token = None
            bag.expires_at = None
            bag.save()

            invoice.amount_breakdown = actions.calculate_invoice_breakdown(
                bag,
                invoice,
                lang,
                chosen_period=chosen_period,
                how_many_installments=how_many_installments,
                financing_option_id=financing_option_id,
            )
            invoice.save(update_fields=["amount_breakdown"])

            coupons = bag.coupons.all()
            if coupons.exists() and original_price > 0:
                try:
                    actions.create_seller_reward_coupons(list(coupons), original_price, invoice.user)
                except Exception:
                    pass

            transaction.savepoint_commit(sid)

            has_plan_addons = bag.plan_addons.exists()

            if original_price == 0:
                tasks.build_free_subscription.delay(bag.id, invoice.id, conversion_info="")
            elif bag.how_many_installments > 0:
                tasks.build_plan_financing.delay(bag.id, invoice.id, conversion_info="", externally_managed=True)
                if has_plan_addons:
                    actions.build_plan_addons_financings(bag, invoice, lang, conversion_info="")
            else:
                tasks.build_subscription.delay(bag.id, invoice.id, conversion_info="", externally_managed=True)
                if has_plan_addons:
                    actions.build_plan_addons_financings(bag, invoice, lang, conversion_info="")

            if plans := bag.plans.all():
                for plan in plans:
                    actions.grant_student_capabilities(
                        invoice.user,
                        plan,
                        selected_cohort=selected_cohort,
                    )

            has_referral_coupons = (
                invoice.status == Invoice.Status.FULFILLED
                and invoice.amount > 0
                and coupons.exclude(referral_type="NO_REFERRAL").exists()
            )

            if has_referral_coupons:
                transaction.on_commit(lambda inv_id=invoice.id: register_referral_from_invoice.delay(inv_id))

            tasks_activity.add_activity.delay(
                invoice.user.id,
                "checkout_completed",
                related_type="payments.Invoice",
                related_id=invoice.id,
            )

        instance.status_texts.pop(handler_key, None)
        instance.status = "DONE" if len(instance.status_texts) == 0 else "ERROR"
        instance.save()

    except Exception as e:
        logger.exception("Stripe checkout payment fulfillment failed for session %s", session_id)
        instance.status_texts[handler_key] = str(e)[:255]
        instance.status = "ERROR"
        instance.save()
        tasks.send_checkout_fulfillment_error_email.delay(bag.id, session_id, str(e)[:200])


@receiver(monitoring_signals.stripe_webhook, sender=StripeEvent)
def stripe_checkout_renewal_fulfillment(sender: Type[StripeEvent], instance: StripeEvent, **kwargs):
    handler_key = "payments.stripe_checkout_renewal_fulfillment"

    if instance.type not in (
        "checkout.session.completed",
        "checkout.session.async_payment_succeeded",
        "checkout.session.async_payment_failed",
    ):
        return

    session = instance.data.get("object") or instance.data
    metadata = session.get("metadata") or {}
    if not metadata.get("bag_id"):
        return

    has_subscription = bool(metadata.get("subscription_id"))
    has_plan_financing = bool(metadata.get("plan_financing_id"))
    if has_subscription and has_plan_financing:
        return
    if not has_subscription and not has_plan_financing:
        return

    if instance.type == "checkout.session.async_payment_failed":
        instance.status_texts[handler_key] = "async payment failed"
        instance.status = "ERROR"
        instance.save()
        return

    payment_status = session.get("payment_status")
    if instance.type == "checkout.session.completed" and payment_status == "unpaid":
        instance.status_texts.pop(handler_key, None)
        instance.status = "DONE" if len(instance.status_texts) == 0 else "ERROR"
        instance.save()
        return

    if payment_status != "paid":
        return

    ctx, error = _load_stripe_checkout_fulfillment_context(
        session,
        require_subscription=has_subscription,
        require_plan_financing=has_plan_financing,
    )
    if error:
        instance.status_texts[handler_key] = error
        instance.status = "ERROR"
        instance.save()
        if metadata.get("bag_id") and session.get("id"):
            tasks.send_checkout_fulfillment_error_email.delay(
                int(float(metadata["bag_id"])),
                session["id"],
                error[:200],
            )
        return
    if not ctx:
        return

    session_id = ctx["session_id"]
    bag = ctx["bag"]
    subscription = ctx.get("subscription")
    plan_financing = ctx.get("plan_financing")
    amount = ctx["amount"]
    original_price = ctx["original_price"]
    payment_method = ctx["payment_method"]
    chosen_period = ctx["chosen_period"]
    lang = ctx["lang"]

    if Invoice.objects.filter(stripe_id=session_id, status=Invoice.Status.FULFILLED).exists():
        instance.status_texts.pop(handler_key, None)
        instance.status = "DONE" if len(instance.status_texts) == 0 else "ERROR"
        instance.save()
        return

    utc_now = timezone.now()

    try:
        with transaction.atomic():
            sid = transaction.savepoint()

            invoice, created = Invoice.objects.get_or_create(
                stripe_id=session_id,
                defaults={
                    "bag": bag,
                    "user": bag.user,
                    "amount": amount,
                    "currency": bag.currency,
                    "status": Invoice.Status.FULFILLED,
                    "externally_managed": True,
                    "academy": bag.academy,
                    "paid_at": utc_now,
                    "payment_method": payment_method,
                },
            )

            if not created and invoice.status == Invoice.Status.FULFILLED:
                transaction.savepoint_rollback(sid)
                instance.status_texts.pop(handler_key, None)
                instance.status = "DONE" if len(instance.status_texts) == 0 else "ERROR"
                instance.save()
                return

            invoice.refresh_from_db()

            bag.status = "PAID"
            if chosen_period:
                bag.chosen_period = chosen_period
            bag.save()

            invoice.amount_breakdown = actions.calculate_invoice_breakdown(
                bag,
                invoice,
                lang,
                chosen_period=chosen_period or bag.chosen_period,
                how_many_installments=0,
            )
            invoice.save(update_fields=["amount_breakdown"])

            coupons = bag.coupons.all()
            if coupons.exists() and original_price > 0:
                try:
                    actions.create_seller_reward_coupons(list(coupons), original_price, invoice.user)
                except Exception:
                    pass

            transaction.savepoint_commit(sid)

            if subscription:
                should_charge_now = (
                    utc_now >= subscription.next_payment_at
                    and subscription.status == Subscription.Status.PAYMENT_ISSUE
                )

                transaction.on_commit(lambda: subscription.invoices.add(invoice))

                if should_charge_now:
                    transaction.on_commit(lambda sub_id=subscription.id: tasks.charge_subscription.delay(sub_id))
            elif plan_financing:
                should_charge_now = (
                    utc_now >= plan_financing.next_payment_at
                    and plan_financing.status == PlanFinancing.Status.PAYMENT_ISSUE
                )

                transaction.on_commit(lambda: plan_financing.invoices.add(invoice))

                if should_charge_now:
                    transaction.on_commit(
                        lambda pf_id=plan_financing.id: tasks.charge_plan_financing.delay(pf_id)
                    )

            tasks_activity.add_activity.delay(
                invoice.user.id,
                "checkout_completed",
                related_type="payments.Invoice",
                related_id=invoice.id,
            )

        instance.status_texts.pop(handler_key, None)
        instance.status = "DONE" if len(instance.status_texts) == 0 else "ERROR"
        instance.save()

    except Exception as e:
        logger.exception("Stripe checkout renewal fulfillment failed for session %s", session_id)
        instance.status_texts[handler_key] = str(e)[:255]
        instance.status = "ERROR"
        instance.save()
        tasks.send_checkout_fulfillment_error_email.delay(bag.id, session_id, str(e)[:200])
