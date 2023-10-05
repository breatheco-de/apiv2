from django.core.management.base import BaseCommand

from breathecode.commons import tasks
from ...models import TaskManager
from datetime import datetime
from datetime import timedelta

TOLERANCE = 30


class Command(BaseCommand):
    help = 'Rerun all the tasks that are pending and were run in the last 10 minutes'

    def handle(self, *args, **options):
        utc_now = datetime.utcnow()
        tolerance = timedelta(minutes=TOLERANCE)
        ids = TaskManager.objects.filter(last_run__lt=utc_now - tolerance,
                                         status='PENDING').values_list('id', flat=True)

        for id in ids:
            tasks.mark_task_as_pending.delay(id, force=True)

        if ids:
            msg = self.style.SUCCESS(f"Rerunning TaskManager's {', '.join([str(id) for id in ids])}")

        else:
            msg = self.style.SUCCESS("No TaskManager's available to re-run")

        self.stdout.write(self.style.SUCCESS(msg))
