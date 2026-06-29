import json
from datetime import timedelta
from urllib.parse import parse_qs, urlparse

from django.contrib.auth.models import User
from django.utils import timezone

from breathecode.authenticate.actions import get_app_url, get_user_settings
from breathecode.admissions.models import Cohort
from breathecode.monitoring import signals as monitoring_signals
from breathecode.monitoring.models import StripeEvent
from breathecode.notify import actions as notify_actions
from breathecode.payments.actions import is_stripe_checkout_already_fulfilled, retry_pending_bag
from breathecode.payments.models import (
    Bag,
    ConsumptionSession,
    Service,
    Consumable,
    Invoice,
    Subscription,
    SubscriptionBillingTeam,
    SubscriptionSeat,
    ServiceStockScheduler,
    Plan,
    STRIPE_CHECKOUT_FULFILLMENT_EVENT_TYPES,
)
from breathecode.payments.tasks import (
    build_service_stock_scheduler_from_subscription,
)
from breathecode.utils.decorators import issue, supervisor

MIN_PENDING_SESSIONS = 30
MIN_CANCELLED_SESSIONS = 10


@supervisor(delta=timedelta(days=1))
def supervise_all_consumption_sessions():
    """Aggregates daily anomalies for consumption sessions (pending/cancelled ratios)."""
    utc_now = timezone.now()

    done_sessions = ConsumptionSession.objects.filter(
        status="DONE", eta__lte=utc_now, eta__gte=utc_now - timedelta(days=1)
    )
    pending_sessions = ConsumptionSession.objects.filter(
        status="PENDING", eta__lte=utc_now, eta__gte=utc_now - timedelta(days=1)
    )

    done_amount = done_sessions.count()
    pending_amount = pending_sessions.count()

    if (
        pending_amount
        and done_amount
        and (rate := pending_amount / done_amount) >= 0.3
        and done_amount > MIN_PENDING_SESSIONS
    ):
        yield f"There has so much pending consumption sessions, {pending_amount} pending and rate {round(rate * 100, 2)}%"

    users = User.objects.filter(
        consumptionsession__status="CANCELLED",
        consumptionsession__eta__lte=utc_now,
        consumptionsession__eta__gte=utc_now - timedelta(days=1),
    ).distinct()

    for user in users:
        done_sessions = ConsumptionSession.objects.filter(
            user=user,
            status="DONE",
            operation_code="unsafe-consume-service-set",
            consumable__service_item__service__type=Service.Type.VOID,
            eta__lte=utc_now - timedelta(minutes=10),
        )
        cancelled_sessions = ConsumptionSession.objects.filter(
            user=user,
            status="CANCELLED",
            operation_code="unsafe-consume-service-set",
            consumable__service_item__service__type=Service.Type.VOID,
            eta__lte=utc_now,
            eta__gte=utc_now - timedelta(days=1),
        )

        done_amount = done_sessions.count()
        cancelled_amount = cancelled_sessions.count()

        # this client should be a cheater
        if (
            cancelled_amount
            and done_amount
            and (rate := cancelled_amount / done_amount) > 0.1
            and done_amount >= MIN_CANCELLED_SESSIONS
        ):
            yield f"There has {round(rate * 100, 2)}% cancelled consumption sessions, due to a bug or a cheater, user {user.email}"


@supervisor(delta=timedelta(minutes=10))
def supervise_pending_bags_to_be_delivered():
    """
    Supervisor to check for bags that are paid but not delivered.
    This helps identify issues in the subscription/plan financing creation process.
    """
    utc_now = timezone.now()

    # Filter bags that are paid but not delivered, updated between 5 and 30 minutes ago
    pending_bags = Bag.objects.filter(
        status="PAID",
        was_delivered=False,
        updated_at__lte=utc_now - timedelta(minutes=30),
        updated_at__gte=utc_now - timedelta(minutes=5),
    )

    pending_count = pending_bags.count()

    if pending_count > 0:
        for bag in pending_bags:
            invoice = bag.invoices.filter(status="FULFILLED").order_by("-paid_at").first()
            if invoice:
                yield (
                    f"Bag {bag.id} for user {bag.user.email} in academy {bag.academy.name} has not been delivered",
                    "pending-bag-delivery",
                    {"bag_id": bag.id},
                )


@supervisor(delta=timedelta(minutes=30))
def supervise_stripe_checkout_events_in_error():
    print("Supervising stripe checkout events in error")
    """
    Detect verified Stripe checkout webhooks that failed after payment succeeded.

    Skips events already fulfilled, unverified signatures, unpaid sessions, and purchase bags
    that should be handled by supervise_pending_bags_to_be_delivered instead.
    """
    utc_now = timezone.now()

    events = StripeEvent.objects.filter(
        status="ERROR",
        type__in=STRIPE_CHECKOUT_FULFILLMENT_EVENT_TYPES,
        created_at__lte=utc_now - timedelta(minutes=5),
        created_at__gte=utc_now - timedelta(days=7),
    ).order_by("id")
    print("Eventsss", events)
    for event in events:
        if (event.status_texts or {}).get("verified") is False:
            continue

        event_data = event.data or {}
        session = event_data.get("object") or event_data
        if session.get("payment_status") != "paid":
            continue

        metadata = session.get("metadata") or {}
        bag_id = metadata.get("bag_id")
        if not bag_id:
            print("No bag ID")
            continue

        try:
            bag_id_int = int(float(bag_id))
            print("Bag ID int", bag_id_int)
        except (TypeError, ValueError):
            continue

        bag = Bag.objects.filter(id=bag_id_int).select_related("user", "academy").first()

        if is_stripe_checkout_already_fulfilled(
            session=session,
            exclude_stripe_event_id=event.id,
        ):
            print("Stripe checkout event already fulfilled")
            continue

        user_email = bag.user.email if bag and bag.user_id else "unknown user"
        academy_name = bag.academy.name if bag and bag.academy_id else "unknown academy"

        yield (
            f"Stripe checkout event {event.id} ({event.type}) failed for bag {bag_id_int} "
            f"user {user_email} academy {academy_name}",
            "stripe-checkout-fulfillment-error",
            {"bag_id": bag_id_int, "stripe_event_id": event.id},
        )


@issue(supervise_stripe_checkout_events_in_error, delta=timedelta(minutes=30), attempts=3)
def stripe_checkout_fulfillment_error(bag_id: int, stripe_event_id: int):
    """
    Replay a failed Stripe checkout webhook to retry payment or renewal fulfillment.
    """
    event = StripeEvent.objects.filter(id=stripe_event_id).first()
    if not event:
        return False

    event_data = event.data or {}
    session = event_data.get("object") or event_data
    metadata = session.get("metadata") or {}
    bag = Bag.objects.filter(id=bag_id).first()

    if is_stripe_checkout_already_fulfilled(
        session=session,
        exclude_stripe_event_id=event.id,
    ):
        return True

    session_id = session.get("id")
    has_session_invoice = bool(
        session_id
        and Invoice.objects.filter(stripe_id=session_id, status=Invoice.Status.FULFILLED).exists()
    )
    is_renewal = metadata.get("subscription_id") or metadata.get("plan_financing_id")
    if (
        not is_renewal
        and bag
        and bag.status != Bag.Status.CHECKING
        and not has_session_invoice
    ):
        return False

    if bag and (raw_snapshot := metadata.get("fulfillment_snapshot")):
        try:
            snapshot = json.loads(raw_snapshot)
            bag.plans.set(snapshot.get("plan_ids") or [])
            bag.plan_addons.set(snapshot.get("plan_addon_ids") or [])
            bag.coupons.set(snapshot.get("coupon_ids") or [])
            if chosen_period := metadata.get("chosen_period"):
                bag.chosen_period = chosen_period
            if raw_installments := metadata.get("how_many_installments"):
                bag.how_many_installments = int(float(raw_installments))
            bag.save(update_fields=["chosen_period", "how_many_installments"])
        except (json.JSONDecodeError, TypeError, ValueError):
            return False

    if not metadata.get("selected_cohort") and (success_url := session.get("success_url")):
        if cohort_ref := parse_qs(urlparse(success_url).query).get("cohort", [None])[0]:
            selected_cohort = cohort_ref
            try:
                if slug := Cohort.objects.filter(id=int(cohort_ref)).values_list("slug", flat=True).first():
                    selected_cohort = slug
            except (TypeError, ValueError):
                pass
            metadata["selected_cohort"] = selected_cohort
            event.data = event_data
            event.save(update_fields=["data"])

    monitoring_signals.stripe_webhook.send_robust(instance=event, sender=event.__class__)

    event.refresh_from_db()
    if event.status == "DONE":
        user = None
        if metadata.get("user_id"):
            try:
                user = User.objects.filter(id=int(float(metadata["user_id"]))).first()
            except (TypeError, ValueError):
                pass
        if not user and metadata.get("user_email"):
            user = User.objects.filter(email=metadata["user_email"]).first()

        if user:
            user_settings = get_user_settings(user.id)
            lang = user_settings.lang if user_settings and user_settings.lang else "en"
            invoice = (
                Invoice.objects.filter(stripe_id=session_id).select_related("academy").first() if session_id else None
            )
            academy = invoice.academy if invoice else (bag.academy if bag else None)
            messages = {
                "en": {
                    "subject": "Your plan has been activated",
                    "message": f"Hello {user.first_name or 'there'},<br><br>"
                    f"Your plan has been activated successfully.<br><br>",
                    "button": "Go to programs",
                },
                "es": {
                    "subject": "Tu plan se activó correctamente",
                    "message": f"Hola {user.first_name or ''},<br><br>"
                    f"Tu plan se activó correctamente.<br><br>",
                    "button": "Ir a los programas",
                },
            }
            selected_lang = lang if lang in messages else "en"
            notify_actions.send_email_message(
                "message",
                user.email,
                {
                    "SUBJECT": messages[selected_lang]["subject"],
                    "MESSAGE": messages[selected_lang]["message"],
                    "BUTTON": messages[selected_lang]["button"],
                    "LINK": f"{get_app_url(academy)}/choose-program",
                },
                academy=academy,
            )
        return True

    return None


@issue(supervise_pending_bags_to_be_delivered, delta=timedelta(minutes=30), attempts=3)
def pending_bag_delivery(bag_id: int):
    """
    Issue handler for pending bag delivery.
    This function is called when a bag is detected as paid but not delivered.
    It will attempt to retry the delivery process.
    """
    # Check if the bag still needs to be processed
    bag = Bag.objects.filter(id=bag_id, status="PAID", was_delivered=False).first()
    if not bag:
        # Bag was already delivered or doesn't exist, mark as fixed
        return True

    # Call the task to retry the delivery
    res = retry_pending_bag(bag)

    if res == "done":
        return True

    if res == "scheduled":
        return None

    return False


# ------------------------------
# Seats & Billing Team Supervisors
# ------------------------------


def _effective_strategy(plan: Plan | None) -> str | None:
    if not plan:
        return None
    return (
        plan.consumption_strategy
        if plan.consumption_strategy != Plan.ConsumptionStrategy.BOTH
        else Plan.ConsumptionStrategy.PER_SEAT
    )


@supervisor(delta=timedelta(minutes=15))
def supervise_billing_team_strategy():
    """Detect teams whose strategy drifted from the subscription plan strategy."""
    for team in SubscriptionBillingTeam.objects.select_related("subscription").iterator():
        sub = team.subscription
        if not sub:
            continue
        plan = sub.plans.first()
        expected = _effective_strategy(plan)
        if expected and team.consumption_strategy != expected:
            yield (
                f"Team {team.id} strategy {team.consumption_strategy} != {expected}",
                "billing-team-strategy-mismatch",
                {
                    "subscription_id": sub.id,
                    "team_id": team.id,
                    "expected_strategy": expected,
                    "current_strategy": team.consumption_strategy,
                },
            )


@issue(supervise_billing_team_strategy, delta=timedelta(minutes=30), attempts=3)
def billing_team_strategy_mismatch(subscription_id: int, team_id: int, expected_strategy: str, current_strategy: str):
    """Fix team strategy drift by normalizing and scheduling a rebuild. Returns None (scheduled)."""
    team = SubscriptionBillingTeam.objects.filter(id=team_id, subscription__id=subscription_id).first()
    if not team:
        return True
    if team.consumption_strategy == expected_strategy:
        return True
    team.consumption_strategy = expected_strategy
    team.save(update_fields=["consumption_strategy"])
    # schedule rebuild to reflect strategy change in schedulers
    build_service_stock_scheduler_from_subscription.delay(subscription_id)
    # None => scheduled; supervisor should reattempt to verify state
    return None


@supervisor(delta=timedelta(minutes=10))
def supervise_owner_seat():
    """Ensure the subscription owner has a seat when a billing team exists."""
    qs = Subscription.objects.filter(has_billing_team=True).select_related("user")
    for sub in qs.iterator():
        team = SubscriptionBillingTeam.objects.filter(subscription=sub).first()
        if not team:
            # flag drift will handle this
            continue
        exists = SubscriptionSeat.objects.filter(billing_team=team, user=sub.user).exists()
        if not exists:
            owner_email = (sub.user.email or "").strip().lower()
            yield (
                f"Owner seat missing for subscription {sub.id}",
                "owner-seat-missing",
                {"subscription_id": sub.id, "team_id": team.id, "user_id": sub.user.id, "email": owner_email},
            )


@issue(supervise_owner_seat, delta=timedelta(minutes=30), attempts=3)
def owner_seat_missing(subscription_id: int, team_id: int, user_id: int, email: str):
    """Create/reactivate owner seat. Returns False if team missing, True if ensured."""
    team = SubscriptionBillingTeam.objects.filter(id=team_id, subscription__id=subscription_id).first()
    if not team:
        # cannot fix in this handler, flag drift supervisor should handle missing team
        return False
    SubscriptionSeat.objects.get_or_create(
        billing_team=team,
        user_id=user_id,
        defaults={"email": email, "is_active": True},
    )
    return True


@supervisor(delta=timedelta(minutes=30))
def supervise_scheduler_configuration():
    """Detect scheduler topology drift based on team strategy (PER_TEAM vs PER_SEAT)."""
    for team in SubscriptionBillingTeam.objects.select_related("subscription").iterator():
        sub = team.subscription
        if not sub:
            continue
        plan = sub.plans.first()
        expected = _effective_strategy(plan)
        if not expected:
            continue

        has_team_sched = ServiceStockScheduler.objects.filter(subscription_billing_team=team).exists()
        has_seat_sched = ServiceStockScheduler.objects.filter(subscription_seat__billing_team=team).exists()

        if expected == Plan.ConsumptionStrategy.PER_SEAT and has_team_sched:
            yield (
                f"Team {team.id} has team schedulers under PER_SEAT",
                "scheduler-configuration-drift",
                {"subscription_id": sub.id, "team_id": team.id, "strategy": expected},
            )

        if expected == Plan.ConsumptionStrategy.PER_TEAM and has_seat_sched:
            yield (
                f"Team {team.id} has seat schedulers under PER_TEAM",
                "scheduler-configuration-drift",
                {"subscription_id": sub.id, "team_id": team.id, "strategy": expected},
            )


# write solution if needed
# @issue(supervise_scheduler_configuration, delta=timedelta(minutes=30), attempts=3)
# def scheduler_configuration_drift(subscription_id: int, team_id: int, strategy: str):
#     """Schedule a rebuild of schedulers to repair topology drift. Returns None (scheduled)."""
#     # simplest repair: rebuild schedulers based on current business logic
#     build_service_stock_scheduler_from_subscription.delay(subscription_id)
#     # None => scheduled; supervisor should reattempt to verify state
#     return None


@supervisor(delta=timedelta(minutes=30))
def supervise_billing_team_flag_drift():
    """Detect drift between subscription.has_billing_team and real team existence."""
    for sub in Subscription.objects.all().iterator():
        team_exists = SubscriptionBillingTeam.objects.filter(subscription=sub).exists()
        if bool(sub.has_billing_team) != bool(team_exists):
            yield (
                f"Subscription {sub.id} has_billing_team={sub.has_billing_team} but team_exists={team_exists}",
                "billing-team-flag-drift",
                {"subscription_id": sub.id, "expected": bool(team_exists), "current": bool(sub.has_billing_team)},
            )


@issue(supervise_billing_team_flag_drift, delta=timedelta(minutes=30), attempts=3)
def billing_team_flag_drift(subscription_id: int, expected: bool, current: bool):
    """Normalize has_billing_team flag to reflect actual team existence. Returns True when saved."""
    sub = Subscription.objects.filter(id=subscription_id).first()
    if not sub:
        return True
    if bool(sub.has_billing_team) == bool(expected):
        return True
    sub.has_billing_team = expected
    sub.save(update_fields=["has_billing_team"])
    return True


@supervisor(delta=timedelta(minutes=30))
def supervise_team_seat_consumables():
    """
    Detect consumable ownership drift for teams:
    - PER_SEAT: team-owned consumables should not exist.
    - PER_TEAM: seat-owned consumables should not exist.
    This complements scheduler drift checks by validating emitted consumables.
    """
    for team in SubscriptionBillingTeam.objects.select_related("subscription").iterator():
        sub = team.subscription
        if not sub:
            continue
        plan = sub.plans.first()
        expected = _effective_strategy(plan)
        if not expected:
            continue

        # Ownership presence flags
        has_team_owned = Consumable.objects.filter(subscription_billing_team=team).exists()
        has_seat_owned = Consumable.objects.filter(subscription_seat__billing_team=team).exists()

        if expected == Plan.ConsumptionStrategy.PER_SEAT and has_team_owned:
            yield (
                f"Team {team.id} has team-owned consumables under PER_SEAT",
                "consumable-owner-drift",
                {"subscription_id": sub.id, "team_id": team.id, "strategy": expected},
            )

        if expected == Plan.ConsumptionStrategy.PER_TEAM and has_seat_owned:
            yield (
                f"Team {team.id} has seat-owned consumables under PER_TEAM",
                "consumable-owner-drift",
                {"subscription_id": sub.id, "team_id": team.id, "strategy": expected},
            )


# write solution if needed
# @issue(supervise_team_seat_consumables, delta=timedelta(minutes=30), attempts=3)
# def consumable_owner_drift(subscription_id: int, team_id: int, strategy: str):
#     """
#     Attempt to repair consumable ownership drift by rebuilding schedulers and renewing consumables.
#     - PER_SEAT: renew owner-level and per-seat consumables for each active seat.
#     - PER_TEAM: renew team-owned/owner-level consumables.
#     Returns None (scheduled) to let the supervisor re-check in the next run.
#     """
#     team = SubscriptionBillingTeam.objects.filter(id=team_id, subscription__id=subscription_id).first()
#     if not team:
#         return True  # already fixed by deletion

#     # Rebuild schedulers first
#     build_service_stock_scheduler_from_subscription.delay(subscription_id)

#     if strategy == Plan.ConsumptionStrategy.PER_SEAT:
#         # Renew owner-level once
#         renew_subscription_consumables.delay(subscription_id)
#         # Renew for each active seat
#         for seat in SubscriptionSeat.objects.filter(billing_team=team, is_active=True):
#             renew_subscription_consumables.delay(subscription_id, seat_id=seat.id)
#     else:
#         # PER_TEAM: a single renew should be enough
#         renew_subscription_consumables.delay(subscription_id)

#     return None
