from django.core.management.base import BaseCommand
from breathecode.payments.models import Consumable


class Command(BaseCommand):
    help = "Deletes all consumables that are not linked to any subscription or plan financing."

    def handle(self, *args, **options):
        count = Consumable.objects.filter(subscription__isnull=True, plan_financing__isnull=True).count()
        Consumable.objects.filter(subscription__isnull=True, plan_financing__isnull=True).delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {count} orphan consumables."))
