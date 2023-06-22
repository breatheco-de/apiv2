import os, requests, sys, pytz
from datetime import datetime
from django.db.models import Q
from django.core.management.base import BaseCommand, CommandError
from breathecode.admissions.models import CohortUser
from ...actions import delete_tokens
from ...models import ProfileAcademy, Role, UserInvite


class Command(BaseCommand):
    help = 'Confirm all the emails that are not from a saas academy'

    def handle(self, *args, **options):
        invites = UserInvite.objects.filter(Q(academy__available_as_saas=False)
                                            | Q(cohort__academy__available_as_saas=False),
                                            is_email_validated=False)

        n = invites.count()
        invites.update(is_email_validated=True)

        self.stdout.write(self.style.SUCCESS(f'Successfully confirmed {n} invites'))
