from datetime import timedelta
from django.core.management.base import BaseCommand
from ...models import ServiceStockScheduler
from django.utils import timezone
from django.db.models import Max


class Command(BaseCommand):
    help = "Update unsync consumables and their service stock schedulers"

    def handle(self, *args, **options):
        self.utc_now = timezone.now()
        self.update_unsync_schedulers()

    def update_unsync_schedulers(self):
        # Buscar schedulers que tienen valid_until menor que ahora pero cumplen con las condiciones
        stock_schedulers_to_update = ServiceStockScheduler.objects.annotate(
            last_consumable_valid_until=Max("consumables__valid_until")
        ).filter(
            valid_until__lt=self.utc_now,  # el scheduler expiró
            last_consumable_valid_until__lte=self.utc_now + timedelta(hours=2),  # el último consumible expira pronto
        ).filter(
            # Condiciones para subscriptions
            plan_handler__subscription__next_payment_at__gt=self.utc_now,
        ).exclude(
            plan_handler__subscription__status__in=["CANCELLED", "DEPRECATED", "PAYMENT_ISSUE"]
        ) | ServiceStockScheduler.objects.annotate(
            last_consumable_valid_until=Max("consumables__valid_until")
        ).filter(
            valid_until__lt=self.utc_now,  # el scheduler expiró
            last_consumable_valid_until__lte=self.utc_now + timedelta(hours=2),  # el último consumible expira pronto
        ).filter(
            # Condiciones para plan financings
            plan_handler__plan_financing__next_payment_at__gt=self.utc_now,
        ).exclude(
            plan_handler__plan_financing__status__in=["CANCELLED", "DEPRECATED", "PAYMENT_ISSUE"]
        )

        updated_count = 0
        for scheduler in stock_schedulers_to_update:
            # Actualizar el scheduler
            scheduler.valid_until = self.utc_now + timedelta(hours=2)
            scheduler.save()

            # Actualizar todos los consumibles asociados usando la relación directa
            scheduler.consumables.all().update(valid_until=self.utc_now + timedelta(hours=2))

            updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(f"Successfully updated {updated_count} service stock schedulers and their consumables")
        )
