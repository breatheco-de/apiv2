from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from capyc.core.i18n import translation
from breathecode.notify import actions as notify_actions
from breathecode.utils.decorators import issue, supervisor

from .models import Consumable, Subscription, SubscriptionSeat, ServiceItem
from . import actions as payments_actions


@supervisor(delta=timedelta(minutes=15))
def supervise_orphaned_team_members():
    """Detect team members without required per-policy consumables and propose fixes.

    For each seat on a team-enabled item, ensure per-member consumables exist per service_slug in the policy.
    """
    utc_now = timezone.now()

    seats = SubscriptionSeat.objects.select_related("subscription", "user").all()

    for seat in seats:
        # evaluate against all team-enabled policy items in the subscription
        policy_items = ServiceItem.objects.filter(plan__subscription=seat.subscription, is_team_allowed=True).distinct()
        entries = []
        for policy_item in policy_items:
            entries.extend((policy_item.team_consumables or {}).get("allowed") or [])
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            service_slug = entry.get("service_slug")
            if not service_slug:
                continue

            exists = (
                Consumable.objects.filter(
                    user=seat.user,
                    subscription=seat.subscription,
                    service_item__service__slug=service_slug,
                )
                .filter(Q(valid_until__gte=utc_now) | Q(valid_until=None))
                .exclude(how_many=0)
                .exists()
            )

            if not exists:
                yield {
                    "code": "fix-orphaned-team-member",
                    "message": f"Missing consumable for user {seat.user_id} service {service_slug}",
                    "params": {"seat_id": seat.id, "service_slug": service_slug},
                }


@issue(supervise_orphaned_team_members, delta=timedelta(minutes=30), attempts=3)
def fix_orphaned_team_member(seat_id: int, service_slug: str):
    """Create missing consumables for a seat; idempotent via action helper."""
    seat = SubscriptionSeat.objects.select_related("subscription", "user").filter(id=seat_id).first()
    if not seat:
        return True

    before = (
        Consumable.objects.filter(
            user=seat.user, subscription=seat.subscription, service_item__service__slug=service_slug
        )
        .exclude(how_many=0)
        .count()
    )

    # apply policy across all team-enabled items
    policy_items = ServiceItem.objects.filter(plan__subscription=seat.subscription, is_team_allowed=True).distinct()
    for policy_item in policy_items:
        payments_actions.create_team_member_consumables(
            subscription=seat.subscription, user=seat.user, policy_item=policy_item
        )

    after = (
        Consumable.objects.filter(
            user=seat.user, subscription=seat.subscription, service_item__service__slug=service_slug
        )
        .exclude(how_many=0)
        .count()
    )

    return after > 0 or before > 0


@supervisor(delta=timedelta(minutes=20))
def supervise_team_member_limits():
    """Detect subscriptions where team size (members+invites) exceeds configured max_team_members."""
    subs = Subscription.objects.all()
    for sub in subs:
        # find distinct team-enabled items linked to this subscription via seats
        for item in ServiceItem.objects.filter(plan__subscription=sub, is_team_allowed=True).distinct():
            if item.max_team_members is None or item.max_team_members < 0:
                continue
            members = SubscriptionSeat.objects.filter(subscription=sub).exclude(user__isnull=True).count()
            invites = SubscriptionSeat.objects.filter(subscription=sub, user__isnull=True).count()
            total = members + invites
            if total > item.max_team_members:
                yield {
                    "code": "fix-team-size-exceeded",
                    "message": f"Team size {total} exceeds limit {item.max_team_members} for subscription {sub.id}",
                    "params": {"subscription_id": sub.id, "service_item_id": item.id, "total": total},
                }


@issue(supervise_team_member_limits, delta=timedelta(hours=1), attempts=1)
def fix_team_size_exceeded(subscription_id: int, service_item_id: int, total: int):
    """Notify owner when team size exceeds limits. No destructive action by default."""
    sub = Subscription.objects.filter(id=subscription_id).first()
    item = ServiceItem.objects.filter(id=service_item_id).first()
    if not sub or not item:
        return True

    lang = "en"
    subject = translation(
        lang,
        en="Your team exceeds the configured limit",
        es="Tu equipo excede el límite configurado",
    )
    message = translation(
        lang,
        en=f"Your subscription {subscription_id} has {total} members+invites for {item.service.slug}, which exceeds the configured limit.",
        es=f"Tu suscripción {subscription_id} tiene {total} miembros+invitaciones para {item.service.slug}, lo cual excede el límite configurado.",
    )

    notify_actions.send_email_message(
        "message",
        sub.user.email,
        {"SUBJECT": subject, "MESSAGE": message},
        academy=sub.academy,
    )

    return True
