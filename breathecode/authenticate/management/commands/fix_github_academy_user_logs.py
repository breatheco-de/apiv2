from django.core.management.base import BaseCommand

from breathecode.admissions.models import Academy
from ...models import GithubAcademyUserLog, User


class Command(BaseCommand):
    help = "Fix github academy user logs valid_until"

    def handle(self, *args, **options):

        users = User.objects.filter(githubacademyuser__isnull=False).distinct()
        academies = Academy.objects.filter()

        for user in users:
            for academy in academies:
                logs = GithubAcademyUserLog.objects.filter(
                    academy_user__user=user, academy_user__academy=academy
                ).order_by("created_at")

                prev = None
                for log in logs:
                    log.valid_until = None
                    log.save()

                    if prev:
                        prev.valid_until = log.created_at
                        prev.save()

                    prev = log
