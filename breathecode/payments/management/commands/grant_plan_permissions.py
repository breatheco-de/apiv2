from django.core.management.base import BaseCommand
from breathecode.payments.models import Subscription, PlanFinancing
from django.contrib.auth.models import Group
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Grant plan permissions to users with active subscriptions and plan financings"

    def handle(self, *args, **options):
        # Get or create the Paid Student group
        group, _ = Group.objects.get_or_create(name="Paid Student")

        # Get all users with active subscriptions or plan financings
        active_users = set()

        # Add users with active subscriptions
        subscriptions = Subscription.objects.filter(status="ACTIVE")
        self.stdout.write(f"Found {subscriptions.count()} active subscriptions")
        for subscription in subscriptions:
            active_users.add(subscription.user)

        # Add users with active plan financings
        plan_financings = PlanFinancing.objects.filter(status="ACTIVE")
        self.stdout.write(f"Found {plan_financings.count()} active plan financings")
        for plan_financing in plan_financings:
            active_users.add(plan_financing.user)

        self.stdout.write(f"Found {len(active_users)} users with active subscriptions or plan financings")

        # Add users to the group
        for user in active_users:
            try:
                if not user.groups.filter(name="Paid Student").exists():
                    user.groups.add(group)
                    self.stdout.write(self.style.SUCCESS(f"Successfully added user {user.email} to Paid Student group"))
            except Exception as e:
                logger.error(f"Error adding user {user.email} to Paid Student group: {str(e)}")
                self.stdout.write(self.style.ERROR(f"Error adding user {user.email} to Paid Student group: {str(e)}"))

        self.stdout.write(self.style.SUCCESS("Successfully completed updating Paid Student group memberships"))
