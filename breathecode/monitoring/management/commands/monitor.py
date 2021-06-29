import os, requests, sys, pytz, datetime
from django.utils import timezone
from django.db.models.expressions import RawSQL
from django.core.management.base import BaseCommand, CommandError
from django.db import models as DM
from django.db.models import Q, F
from ...models import Application, MonitorScript
from ...tasks import monitor_app, execute_scripts
from ...actions import run_script


class BaseSQL(object):
    template = "NOW() - INTERVAL '1 MINUTE' * %(expressions)s"


class DurationAgr(BaseSQL, DM.Aggregate):
    def __init__(self, expression, **extra):
        super(DurationAgr, self).__init__(expression,
                                          output_field=DM.DateTimeField(),
                                          **extra)


class Command(BaseCommand):
    help = 'Sync academies from old breathecode'

    def add_arguments(self, parser):
        parser.add_argument('entity', type=str)
        parser.add_argument(
            '--override',
            action='store_true',
            help='Delete and add again',
        )
        parser.add_argument('--limit',
                            action='store',
                            dest='limit',
                            type=int,
                            default=0,
                            help='How many to import')

    def handle(self, *args, **options):
        try:
            func = getattr(self, options['entity'], None)
        except TypeError:
            self.stderr.write(
                self.style.ERROR(
                    f'Sync method for {options["entity"]} no Found!'))
            return
        except KeyError:
            self.stderr.write(self.style.ERROR('Entity arguments is not set'))
            return

        if not callable(func):
            self.stderr.write(self.style.ERROR('Entity not found'))
            return

        func(options)

    def apps(self, options):
        apps = Application.objects.all().values_list('id', flat=True)

        for app_id in apps:
            monitor_app.delay(app_id)

        self.stdout.write(
            self.style.SUCCESS(f"Enqueued {len(apps)} apps for diagnostic"))

    def scripts(self, options):
        now = timezone.now()
        scripts = MonitorScript.objects\
                    .filter(Q(last_run__isnull=True) | Q(last_run__lte= now - F('frequency_delta')))\
                    .exclude(application__paused_until__isnull=False, application__paused_until__gte=now)\
                    .exclude(paused_until__isnull=False, paused_until__gte=now).values_list('id', flat=True)

        for script_id in scripts:
            execute_scripts.delay(script_id)

        self.stdout.write(
            self.style.SUCCESS(
                f"Enqueued {len(scripts)} scripts for execution"))
