import os, requests, sys, pytz
from datetime import datetime
from django.db.models import Q
from django.core.management.base import BaseCommand, CommandError
from breathecode.admissions.models import CohortUser
from ...actions import delete_tokens
from ...models import GithubAcademyUserLog, GithubAcademyUser, Role, User


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
