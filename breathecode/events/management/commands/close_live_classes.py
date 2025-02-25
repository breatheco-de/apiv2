from datetime import timedelta
from typing import Any
from django.core.management.base import BaseCommand

from ...models import LiveClass
from django.utils import timezone


class Command(BaseCommand):
    help = "Close live classes"

    def handle(self, *args: Any, **options: Any):
        utc_now = timezone.now()
        live_classes = LiveClass.objects.filter(ended_at=None, ending_at__lt=utc_now)

        self.stdout.write(self.style.NOTICE(f"Found {live_classes.count()} live classes to check."))

        for live_class in live_classes:
            ended_at = live_class.ending_at + timedelta(minutes=30)
            if ended_at < utc_now:
                live_class.ended_at = ended_at
                live_class.save()
                self.stdout.write(self.style.SUCCESS(f"Closed live class {live_class.id}"))
            else:
                self.stdout.write(self.style.WARNING(f"Live class {live_class.id} has not ended yet"))
