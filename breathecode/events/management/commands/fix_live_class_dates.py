from django.core.management.base import BaseCommand

from breathecode.admissions.models import Cohort, CohortTimeSlot
from django.utils import timezone

from breathecode.events import tasks


class Command(BaseCommand):
    help = "Fix live classes"

    def handle(self, *args, **options):
        utc_now = timezone.now()

        cohorts = Cohort.objects.filter(ending_date__gte=utc_now, never_ends=False).exclude(
            stage__in=["DELETED", "PREWORK"]
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Found {str(cohorts.count())} cohorts that have not finished and should have live classes"
            )
        )

        for cohort in cohorts:
            timeslots = CohortTimeSlot.objects.filter(cohort=cohort)
            total_cohort_timeslots = timeslots.count()

            if total_cohort_timeslots == 0:
                continue

            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Adding cohort {cohort.slug} to the fixing queue, it ends on {cohort.ending_date}"
                    )
                )
                for timeslot in timeslots:
                    tasks.fix_live_class_dates.delay(timeslot.id)
