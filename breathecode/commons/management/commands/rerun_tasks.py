from django.core.management.base import BaseCommand

from breathecode.commons.tasks import mark_task_as_pending
from ...models import TaskManager
from datetime import datetime
from datetime import timedelta


class Command(BaseCommand):
    help = 'Delete logs and other garbage'

    def handle(self, *args, **options):
        utc_now = datetime.utcnow()
        tolerance = timedelta(minutes=10)
        ids = TaskManager.objects.filter(last_run__gt=utc_now - tolerance).values_list('id', flat=True)

        for id in ids:
            mark_task_as_pending.delay(id)

        if ids:
            msg = self.style.SUCCESS(f"Rerunning TaskManager's {', '.join([str(id) for id in ids])}")

        else:
            msg = self.style.SUCCESS("No TaskManager's available to re-run")

        self.stdout.write(self.style.SUCCESS(msg))
