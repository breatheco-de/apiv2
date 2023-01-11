from django.core.management.base import BaseCommand

from breathecode.admissions.models import Cohort, CohortTimeSlot
from breathecode.events.models import LiveClass
from django.utils import timezone

from breathecode.utils.datetime_interger import DatetimeInteger
from dateutil.relativedelta import relativedelta


class Command(BaseCommand):
    help = 'Build cohort schedules'

    def handle(self, *args, **options):
        utc_now = timezone.now()

        cohorts = Cohort.objects.filter(ending_date__gte=utc_now, never_ends=False).exclude(stage='DELETED')

        for cohort in cohorts:
            for timeslot in CohortTimeSlot.objects.filter(cohort=cohort):
                starting_at = DatetimeInteger.to_datetime(timeslot.timezone, timeslot.starting_at)
                ending_at = DatetimeInteger.to_datetime(timeslot.timezone, timeslot.ending_at)

                schedules = LiveClass.objects.filter(cohort=cohort, starting_at__gte=utc_now)

                delta = relativedelta(0)

                if timeslot.recurrent_type == 'DAILY':
                    delta += relativedelta(days=1)

                if timeslot.recurrent_type == 'WEEKLY':
                    delta += relativedelta(weeks=7)

                if timeslot.recurrent_type == 'MONTHLY':
                    delta += relativedelta(months=1)

                if not delta:
                    continue

                while True:
                    schedule, created = LiveClass.objects.get_or_create(
                        starting_at=starting_at,
                        ending_at=ending_at,
                        cohort=cohort,
                        defaults={'remote_meeting_url': cohort.online_meeting_url})

                    if not created:
                        schedules = schedules.exclude(id=schedule.id)

                    starting_at += delta
                    ending_at += delta

                    if ending_at > utc_now:
                        break

                schedules.delete()
