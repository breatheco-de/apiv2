import os, requests, sys, pytz, logging
from datetime import datetime
from django.db.models import Q, CharField
from django.db.models.functions import Length
from django.core.management.base import BaseCommand, CommandError
from ...models import ProfileAcademy

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync ProfileAcademy first and last name with User.first_name or last_name'

    def handle(self, *args, **options):
        CharField.register_lookup(Length, 'length')
        students_to_sync = ProfileAcademy.objects.filter(Q(first_name__isnull=True) | Q(
            first_name='')).exclude(Q(user__first_name__isnull=True) | Q(user__first_name=''))
        logger.debug(f'Found {students_to_sync.count()} students to sync')
        for stu in students_to_sync:
            if stu.user.first_name != '':
                logger.debug(f'Updating student first name for {stu.user.first_name}')
                stu.first_name = stu.user.first_name
            if stu.user.last_name != '':
                stu.last_name = stu.user.last_name
            stu.save()

        logger.debug(f'Finished.')
