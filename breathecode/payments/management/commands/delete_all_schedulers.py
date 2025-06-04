from django.core.management.base import BaseCommand
from breathecode.payments.models import ServiceStockScheduler


class Command(BaseCommand):
    help = "Deletes ALL ServiceStockSchedulers. This operation is irreversible!"

    def handle(self, *args, **options):
        count = ServiceStockScheduler.objects.count()
        self.stdout.write(
            self.style.WARNING(f"You are about to delete {count} ServiceStockSchedulers. Are you sure? (y/n): ")
        )
        confirm = input().strip().lower()
        if confirm != "y":
            self.stdout.write(self.style.ERROR("Operation cancelled. Nothing was deleted."))
            return

        ServiceStockScheduler.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {count} ServiceStockSchedulers."))
