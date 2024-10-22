# import os
# import urllib.parse
# from datetime import timedelta

from django.core.management.base import BaseCommand

from breathecode.mentorship import tasks
from breathecode.mentorship.models import MentorProfile


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
