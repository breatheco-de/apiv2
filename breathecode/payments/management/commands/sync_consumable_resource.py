import logging
from django.core.management.base import BaseCommand
from breathecode.payments.models import Subscription, PlanFinancing
from breathecode.payments.tasks import (
    build_service_stock_scheduler_from_subscription,
    build_service_stock_scheduler_from_plan_financing,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Creates consumables for active subscriptions and plan financings, "
        "using the same logic as when a user purchases a subscription or plan financing."
    )

    def handle(self, *args, **options):
        created = 0

        # Process active subscriptions
        for subscription in Subscription.objects.filter(status__in=["ACTIVE", "FREE_TRIAL"]):
            self.stdout.write(f"Processing subscription {subscription.id} for user {subscription.user.email}")

            # Build schedulers and consumables for this subscription
            build_service_stock_scheduler_from_subscription.delay(subscription.id)
            created += 1

        # Process active plan financings
        for plan_financing in PlanFinancing.objects.filter(status__in=["ACTIVE", "FULLY_PAID"]):
            self.stdout.write(f"Processing plan financing {plan_financing.id} for user {plan_financing.user.email}")

            # Build schedulers and consumables for this plan financing
            build_service_stock_scheduler_from_plan_financing.delay(plan_financing.id)
            created += 1

        self.stdout.write(self.style.SUCCESS(f"{created} schedulers managed for subscriptions and plan financings."))
