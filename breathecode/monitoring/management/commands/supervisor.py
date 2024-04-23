from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from breathecode.monitoring.models import Supervisor, SupervisorIssue
from breathecode.monitoring.tasks import run_supervisor
from breathecode.utils.decorators import paths


class Command(BaseCommand):
    help = 'Run all supervisors'

    def handle(self, *args, **options):
        utc_now = timezone.now()

        SupervisorIssue.objects.filter(ran_at__lte=utc_now - timedelta(days=7)).delete()

        for fn_module, fn_name, delta in paths:
            Supervisor.objects.get_or_create(task_module=fn_module,
                                             task_name=fn_name,
                                             defaults={
                                                 'delta': delta,
                                                 'ran_at': None,
                                             })

        supervisors = Supervisor.objects.all()

        for supervisor in supervisors:
            if supervisor.ran_at is None or utc_now - supervisor.delta > supervisor.ran_at:
                run_supervisor.delay(supervisor.id)
                self.stdout.write(
                    self.style.SUCCESS(f'Supervisor {supervisor.task_module}.{supervisor.task_name} scheduled'))
