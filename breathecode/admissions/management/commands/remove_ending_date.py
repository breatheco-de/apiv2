from django.core.management.base import BaseCommand
from django.db.models import Q
from ...models import Cohort


class Command(BaseCommand):
    help = "Remove the ending_date from the never ending cohorts"

    def handle(self, *args, **options):
        for element in Cohort.objects.filter(~Q(ending_date=None), never_ends=True):
            element.ending_date = None
            element.save()
