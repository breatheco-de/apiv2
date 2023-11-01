from django.core.management.base import BaseCommand
from ...models import GithubAcademyUserLog, User


class Command(BaseCommand):
    help = 'Fix github academy user logs valid_until'

    def handle(self, *args, **options):

        users = User.objects.filter(githubacademyuser__isnull=False)

        for user in users:
            logs = GithubAcademyUserLog.objects.filter(valid_until__isnull=True,
                                                       academy_user__user=user).order_by('created_at')

            prev = None
            for log in logs:
                if prev:
                    prev.valid_until = log.created_at
                    prev.save()

                prev = log
