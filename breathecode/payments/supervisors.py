from datetime import timedelta

from django.contrib.auth.models import User
from django.utils import timezone

from breathecode.payments.actions import retry_pending_bag
from breathecode.payments.models import Bag, ConsumptionSession, Service
from breathecode.utils.decorators import issue, supervisor

MIN_PENDING_SESSIONS = 30
MIN_CANCELLED_SESSIONS = 10


@supervisor(delta=timedelta(days=1))
def supervise_all_consumption_sessions():
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
