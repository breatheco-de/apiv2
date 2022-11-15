from django.core.management.base import BaseCommand

from breathecode.admissions.models import Academy, Cohort
from breathecode.payments.models import Currency, Fixture
from django.db.models import Q

from django.utils import timezone


class Command(BaseCommand):
    help = 'Seed the fixtures of services'

    def handle(self, *args, **options):
        for fixture in Fixture.objects.filter(cohort_pattern__isnull=False):
            cohorts = Cohort.objects.filter(Q(stage='INACTIVE') | Q(stage='PREWORK'),
                                            slug__regex=fixture.cohort_pattern,
                                            ending_date__gte=timezone.now()).update(fixture=fixture)

            for cohort in cohorts:
                if not fixture.cohorts.filter(id=cohort.id).exists():
                    fixture.cohorts.add(cohort)
