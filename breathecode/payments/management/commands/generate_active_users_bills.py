from datetime import date

from django.core.management.base import BaseCommand
from django.utils import timezone

from breathecode.payments import tasks
from breathecode.payments.models import AcademyPaymentSettings


class Command(BaseCommand):
    help = (
        "Generate daily ActiveUsersBill snapshots for academies with "
        "internal_billing.active_users_billing.enabled. Schedules one Celery task per academy."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            type=str,
            default=None,
            help="Billing date YYYY-MM-DD (default: today UTC)",
        )
        parser.add_argument(
            "--academy",
            type=int,
            default=None,
            help="Only generate for this academy id",
        )
        parser.add_argument(
            "--sync",
            action="store_true",
            help="Run synchronously instead of scheduling Celery tasks",
        )

    def handle(self, *args, **options):
        from breathecode.payments import actions

        billing_date = options.get("date")
        if billing_date:
            billing_date_obj = date.fromisoformat(billing_date)
        else:
            billing_date_obj = timezone.now().date()
            billing_date = billing_date_obj.isoformat()

        qs = AcademyPaymentSettings.objects.select_related("academy").all()
        academy_id = options.get("academy")
        if academy_id:
            qs = qs.filter(academy_id=academy_id)

        scheduled = 0
        skipped = 0
        for settings in qs:
            config = (settings.internal_billing or {}).get("active_users_billing") or {}
            if not config.get("enabled"):
                skipped += 1
                continue
            if config.get("price_per_user") is None:
                self.stdout.write(
                    self.style.WARNING(
                        f"Skipping academy {settings.academy_id}: enabled but price_per_user missing"
                    )
                )
                skipped += 1
                continue

            if options.get("sync"):
                actions.generate_active_users_bill(settings.academy, billing_date=billing_date_obj)
            else:
                tasks.generate_active_users_bill_task.delay(settings.academy_id, billing_date=billing_date)
            scheduled += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Active users bills: scheduled/ran={scheduled}, skipped={skipped}, date={billing_date}"
            )
        )
