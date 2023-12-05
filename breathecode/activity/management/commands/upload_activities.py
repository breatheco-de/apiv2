import os
from django.core.management.base import BaseCommand
from breathecode.services.google_cloud.big_query import BigQuery
from django.utils import timezone
from django.core.cache import cache
from breathecode.activity import tasks

IS_DJANGO_REDIS = hasattr(cache, 'delete_pattern')


def db_backup_bucket():
    return os.getenv('DB_BACKUP_BUCKET')


def get_activity_sampling_rate():
    env = os.getenv('ACTIVITY_SAMPLING_RATE')
    if env:
        return int(env)

    return 60


class Command(BaseCommand):
    help = 'Delete duplicate cohort users imported from old breathecode'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def handle(self, *args, **options):
        utc_now = timezone.now()
        sampling_rate = get_activity_sampling_rate()
        tomorrow = (utc_now + timezone.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        after_tomorrow = tomorrow + timezone.timedelta(days=1)

        cursor = tomorrow
        while cursor < after_tomorrow:
            cursor += timezone.timedelta(seconds=sampling_rate)
            tasks.upload_activities.apply_async(args=(), eta=cursor)

        self.stdout.write(self.style.SUCCESS('Done!'))
