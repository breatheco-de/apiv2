import os

from django.core.cache import cache
from django.core.management.base import BaseCommand

from breathecode.mentorship import tasks
from breathecode.mentorship.models import MentorProfile

IS_DJANGO_REDIS = hasattr(cache, "delete_pattern")


def db_backup_bucket():
    return os.getenv("DB_BACKUP_BUCKET")


def get_activity_sampling_rate():
    env = os.getenv("ACTIVITY_SAMPLING_RATE")
    if env:
        return int(env)

    return 60


class Command(BaseCommand):
    help = "Delete duplicate cohort users imported from old breathecode"

    def handle(self, *args, **options):
        self.check_mentorship_profiles()

    def check_mentorship_profiles(self):
        self.stdout.write(self.style.SUCCESS("Checking mentorship profiles"))
        mentor_profiles = MentorProfile.objects.filter(status__in=["ACTIVE", "UNLISTED"]).only("id")

        for mentor_profile in mentor_profiles:
            tasks.check_mentorship_profile.delay(mentor_profile.id)

        self.stdout.write(self.style.SUCCESS(f"Scheduled {len(mentor_profiles)} mentorship profiles"))
