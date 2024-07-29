import os
from django.core.management.base import BaseCommand
from ...models import Task

HOST = os.environ.get("OLD_BREATHECODE_API")
DATETIME_FORMAT = "%Y-%m-%d"


class Command(BaseCommand):
    help = "Sync academies from old breathecode"

    def add_arguments(self, parser):
        parser.add_argument("entity", type=str)

    def handle(self, *args, **options):
        try:
            func = getattr(self, options["entity"], "entity_not_found")
        except TypeError:
            print(f'Delete method for {options["entity"]} no Found!')

        func(options)

    def all(self, options):
        Task.objects.all().delete()

    def repeated(self, options):

        count = 0
        for a in Task.objects.all().reverse():
            count += 1
            b = Task.objects.filter(user__id=a.user.id, associated_slug=a.associated_slug).exclude(id=a.id).first()
            if b is not None:
                if a.task_status == "PENDING":
                    a.delete()
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Student: {a.user.email} task {a.associated_slug} with status {a.task_status} was deleted"
                        )
                    )
                elif b.task_status == "PENDING":
                    b.delete()
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Student: {b.user.email} task {b.associated_slug} with status {b.task_status} was deleted"
                        )
                    )
                else:
                    a.delete()
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Student: {a.user.email} task {a.associated_slug} with status {a.task_status} was deleted"
                        )
                    )

        self.stdout.write(self.style.NOTICE(f"Ended with {str(count)} tasks evaluated."))
