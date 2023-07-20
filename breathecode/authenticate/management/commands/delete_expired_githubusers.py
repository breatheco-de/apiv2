import os, requests, sys, pytz
from datetime import datetime
from django.db.models import Q
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from ...actions import sync_organization_members
from ...models import AcademyAuthSettings, GithubAcademyUser
from breathecode.admissions.models import Cohort, CohortUser


class Command(BaseCommand):
    help = 'Delete expired temporal and login tokens'

    def handle(self, *args, **options):
        self.update_inactive_github_users()

    def is_user_active_in_other_cohorts(self, user, current_cohort, academy):
        active_cohorts_count = CohortUser.objects.filter(
            user=user,
            cohort__academy=academy,
            cohort__never_ends=False,
            educational_status='ACTIVE',
        ).exclude(cohort__id__in=[current_cohort.id]).count()
        return active_cohorts_count > 0

    def update_inactive_github_users(self):
        added_github_users = GithubAcademyUser.objects.filter(storage_action='ADD')
        print(str(added_github_users.count()) + ' users found')
        for github_user in added_github_users:
            user = github_user.user
            academy = github_user.academy

            try:
                cohort_user = CohortUser.objects.get(
                    user=user,
                    educational_status__in=['POSTPONED', 'SUSPENDED', 'GRADUATED', 'DROPPED'],
                    cohort__academy=academy)
                cohort = cohort_user.cohort

                if not self.is_user_active_in_other_cohorts(user, cohort, academy):
                    github_user.storage_action = 'DELETE'
                    github_user.storage_status = 'PENDING'
                    github_user.save()
                    print(f'Schedule the following github user for deletion in Academy ' +
                          github_user.academy.name + '. User: ' + github_user.user.email)

            except CohortUser.DoesNotExist:
                # Handle the case where the CohortUser entry does not exist (user not in any cohort)
                github_user.storage_action = 'DELETE'
                github_user.storage_status = 'PENDING'
                github_user.save()
