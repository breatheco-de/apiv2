from django.core.management.base import BaseCommand

from breathecode.commons import tasks
from breathecode.notify.actions import send_email_message
from ...models import TaskManager, TaskWatcher
from datetime import datetime, timedelta
from django.db.models import Q

TOLERANCE = 30

HOUR = 19
MINUTE = 0

STATUSES = [
    'PENDING',
    'DONE',
    'CANCELLED',
    'REVERSED',
    'PAUSED',
    'ABORTED',
    'ERROR',
]


def is_report_time():
    # Getting the current datetime
    now = datetime.now()

    # Constructing the starting and ending datetime objects
    start_time = datetime.strptime(f'{now} {HOUR}:{MINUTE}', '%Y-%m-%d %H:%M')
    start_time = start_time.replace(tzinfo=now.tzinfo)
    start_time.second = 0
    start_time.microsecond = 0

    end_time = start_time + timedelta(minutes=10)

    # Comparing and returning the result
    return start_time <= now < end_time


class Command(BaseCommand):
    help = 'Rerun all the tasks that are pending and were run in the last 10 minutes'

    def handle(self, *args, **options):
        self.utc_now = datetime.utcnow()
        self.rerun_pending_tasks()
        self.daily_report()

    def rerun_pending_tasks(self):
        tolerance = timedelta(minutes=TOLERANCE)
        ids = TaskManager.objects.filter(last_run__lt=self.utc_now - tolerance,
                                         status='PENDING').values_list('id', flat=True)

        for id in ids:
            tasks.mark_task_as_pending.delay(id, force=True)

        if ids:
            msg = self.style.SUCCESS(f"Rerunning TaskManager's {', '.join([str(id) for id in ids])}")

        else:
            msg = self.style.SUCCESS("No TaskManager's available to re-run")

        self.stdout.write(self.style.SUCCESS(msg))

    def daily_report(self):
        # TODO: uncomment this
        # if not is_report_time():
        #     self.stdout.write(self.style.SUCCESS('Not report time, skipping.'))
        #     return

        tasks = TaskManager.objects.filter()
        errors = tasks.filter(Q(status='ERROR') | Q(status='ABORTED'))
        error_number = errors.count()

        if not error_number:
            self.stdout.write(self.style.SUCCESS('All is ok.'))

        watchers = TaskWatcher.objects.filter()

        if not watchers:
            self.stdout.write(self.style.SUCCESS('No watchers to send notifies.'))
            return

        done = tasks.filter(status='DONE').count()
        cancelled = tasks.filter(status='CANCELLED').count()
        reversed = tasks.filter(status='REVERSED').count()
        paused = tasks.filter(status='PAUSED').count()
        aborted = tasks.filter(status='ABORTED').count()

        message = '\n'.join([
            'Daily report:',
            f'- {error_number} failed tasks.',
            f'- {done} completed tasks.',
            f'- {cancelled} canceled tasks.',
            f'- {reversed} reversed tasks.',
            f'- {paused} paused tasks.',
            f'- {aborted} aborted tasks.',
            '',
        ])

        module_names = list({x.task_module for x in errors})
        report = {}

        for module_name in module_names:
            report[module_name] = {}

            module = errors.filter(task_module=module_name)
            task_names = list({x.task_name for x in module})

            n = 0

            for task_name in task_names:
                if task_name not in report[module_name]:
                    report[module_name][task_name] = {}

                for status in STATUSES:
                    length = tasks.filter(task_module=module_name, task_name=module_name,
                                          status=status).count()

                    if status == 'ERROR':
                        n += length

                    report[module_name][task_name][status] = length

            report[module_name]['abc_total_cba'] = n

        for watcher in watchers:
            send_email_message('task_manager_report',
                               watcher.email or watcher.user.email, {
                                   'report': report,
                                   'errors': errors,
                                   'done': done,
                                   'cancelled': cancelled,
                                   'reversed': reversed,
                                   'paused': paused,
                                   'aborted': aborted,
                               },
                               force=True)
