import logging
from django.db.models import Q, CharField
from django.db.models.functions import Length
from django.core.management.base import BaseCommand
from ...models import ProfileAcademy

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Sync ProfileAcademy first and last name with User.first_name or last_name"

    def handle(self, *args, **options):
        CharField.register_lookup(Length, "length")
        students_to_sync = ProfileAcademy.objects.filter(Q(first_name__isnull=True) | Q(first_name="")).exclude(
            Q(user__first_name__isnull=True) | Q(user__first_name="")
        )
        logger.debug(f"Found {students_to_sync.count()} ProfileAcademy's to sync")
        for stu in students_to_sync:
            if stu.user is None:
                continue

            if stu.user.first_name != "":
                logger.debug(f"Updating student first name for {stu.user.first_name}")
                stu.first_name = stu.user.first_name
            if stu.user.last_name != "":
                stu.last_name = stu.user.last_name
            stu.save()

        students_to_sync = ProfileAcademy.objects.filter(
            Q(user__first_name__isnull=True) | Q(user__first_name="")
        ).exclude(Q(first_name__isnull=True) | Q(first_name=""))
        logger.debug(f"Found {students_to_sync.count()} User's to sync")
        for stu in students_to_sync:
            if stu.user is None:
                logger.debug(f"Skip {stu.first_name} {stu.last_name} because it has not user object")
                continue

            if stu.first_name is not None and len(stu.first_name) > 0:
                logger.debug(f"Updating student first name for {stu.first_name}")
                stu.user.first_name = stu.first_name
            if stu.first_name is not None and len(stu.last_name) > 0:
                stu.user.last_name = stu.last_name
            stu.user.save()

        logger.debug("Finished.")
