from django.core.management.base import BaseCommand

from breathecode.admissions.models import Cohort, CohortTimeSlot
from django.utils import timezone

from breathecode.events import tasks


class Command(BaseCommand):
    help = "Build live classes"

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
                self.stderr.write(
                    self.style.ERROR(
                        f"Cohort {cohort.slug} live classes will not be generated because it does not have timeslots"
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Adding cohort {cohort.slug} to the generation queue, it ends on {str(cohort.ending_date)}"
                    )
                )
                for timeslot in timeslots:
                    tasks.build_live_classes_from_timeslot.delay(timeslot.id)
