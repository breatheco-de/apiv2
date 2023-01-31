from django.core.management.base import BaseCommand
from django.db.models import Q
from ...models import Cohort


class Command(BaseCommand):
    help = 'Remove the kickoff_date from the never ending cohorts'

    def handle(self, *args, **options):
        for element in Cohort.objects.filter(~Q(kickoff_date=None), never_ends=True):
            element.kickoff_date = None
            element.save()
