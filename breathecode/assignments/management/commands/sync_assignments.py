import os
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from ...actions import sync_student_tasks
from breathecode.admissions.models import CohortUser
from django.db.models import Count

HOST = os.environ.get("OLD_BREATHECODE_API")
DATETIME_FORMAT = "%Y-%m-%d"


class Command(BaseCommand):
    help = "Sync academies from old breathecode"

    def add_arguments(self, parser):
        parser.add_argument("entity", type=str)
        parser.add_argument(
            "--cohorts",
            type=str,
            default=None,
            help="Cohorts slugs to sync",
        )
        parser.add_argument(
            "--students",
            type=str,
            default=None,
            help="Cohorts slugs to sync",
        )
        parser.add_argument("--limit", action="store", dest="limit", type=int, default=0, help="How many to import")

    def handle(self, *args, **options):
        try:
            func = getattr(self, options["entity"], "entity_not_found")
        except TypeError:
            print(f'Sync method for {options["entity"]} no Found!')
        func(options)

    def tasks(self, options):

        limit = False
        total = 0
        if "limit" in options and options["limit"]:
            limit = options["limit"]

        if options["students"] is not None:
            emails = options["students"].split(",")
            for email in emails:
                total += 1
                if limit and limit > 0 and total > limit:
                    self.stdout.write(
                        self.style.SUCCESS(f"Stopped at {total} because there was a limit on the command arguments")
                    )
                    return

                user = User.objects.filter(email=email).first()
                if user is None:
                    raise CommandError(f"Student {email} not found new API")

                sync_student_tasks(user)
        else:
            users = CohortUser.objects.filter(role="STUDENT").values("user").annotate(dcount=Count("user"))
            self.stdout.write(self.style.NOTICE(f"Analyzing {users.count()} cohort users"))
            for u in users:
                if limit and limit > 0 and total > limit:
                    self.stdout.write(
                        self.style.SUCCESS(f"Stopped at {total} because there was a limit on the command arguments")
                    )
                    return

                user = User.objects.get(id=u["user"])
                if user.task_set.count() == 0:
                    self.stdout.write(self.style.SUCCESS(f"Fetching tasks for student {user.email}"))
                else:
                    self.stdout.write(self.style.NOTICE(f"Tasks already fetched for {user.email}"))
                    continue

                total += 1
                try:
                    sync_student_tasks(user)
                except Exception:
                    self.stdout.write(self.style.NOTICE(f"Error synching student stasks for {user.email}"))
