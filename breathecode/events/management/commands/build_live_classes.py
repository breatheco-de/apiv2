from django.core.management.base import BaseCommand

from breathecode.admissions.models import Cohort, CohortTimeSlot
from django.utils import timezone

from breathecode.events import tasks


class Command(BaseCommand):
    help = 'Build live classes'

    def handle(self, *args, **options):
        utc_now = timezone.now()

        cohorts = Cohort.objects.filter(ending_date__gte=utc_now, never_ends=False).exclude(stage='DELETED')

        for cohort in cohorts:
            for timeslot in CohortTimeSlot.objects.filter(cohort=cohort):
                tasks.build_live_classes_from_timeslot.delay(timeslot.id)
