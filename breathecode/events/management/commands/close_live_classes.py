from datetime import timedelta
from typing import Any
from django.core.management.base import BaseCommand

from ...models import LiveClass
from django.utils import timezone


class Command(BaseCommand):
    help = "Close live classes"

    def handle(self, *args: Any, **options: Any):
        live_classes = LiveClass.objects.filter(started_at__isnull=False, ended_at=None)
        utc_now = timezone.now()

        for live_class in live_classes:
            ended_at = live_class.ending_at + timedelta(minutes=30)
            if ended_at < utc_now:
                live_class.ended_at = ended_at
                live_class.save()
