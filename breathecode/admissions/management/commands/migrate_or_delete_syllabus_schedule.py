import os
from django.core.management.base import BaseCommand
from django.db.models import Q
from breathecode.admissions.models import Cohort, SyllabusSchedule, SyllabusScheduleTimeSlot


def db_backup_bucket():
    return os.getenv("DB_BACKUP_BUCKET")


class Command(BaseCommand):
    help = "Delete duplicate cohort users imported from old breathecode"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def handle(self, *args, **options):
        cache = {}
        for cohort in Cohort.objects.filter(
            schedule__academy=None, schedule__isnull=False, academy__timezone__isnull=False
        ):
            if cohort.schedule.id not in cache:
                cache[cohort.schedule.id] = cohort.schedule

            schedule = cache[cohort.schedule.id]

            if schedule.academy:
                if schedule.academy == cohort.academy:
                    pass

                schedule_kwargs = {
                    "academy": cohort.academy,
                    "name": schedule.name,
                    "schedule_type": schedule.schedule_type,
                    "description": schedule.description,
                    "syllabus": schedule.syllabus,
                }

                replica_of_schedule = SyllabusSchedule(**schedule_kwargs)
                replica_of_schedule.save()

                timeslots = SyllabusScheduleTimeSlot.objects.filter(schedule=schedule)

                for timeslot in timeslots:
                    replica_of_timeslot = SyllabusScheduleTimeSlot(
                        recurrent=timeslot.recurrent,
                        starting_at=timeslot.starting_at,
                        ending_at=timeslot.ending_at,
                        schedule=replica_of_schedule,
                        timezone=cohort.timezone or cohort.academy.timezone,
                    )

                    replica_of_timeslot.save()

                cohort.schedule = replica_of_schedule
                cohort.save()

                cache[cohort.schedule.id] = cohort.schedule

            else:
                schedule.academy = cohort.academy
                schedule.save()

                SyllabusScheduleTimeSlot.objects.filter(schedule=schedule).update(
                    timezone=cohort.timezone or cohort.academy.timezone
                )

                cache[schedule.id] = schedule

        SyllabusSchedule.objects.filter(Q(academy=None) | Q(academy__timezone=None)).delete()
        self.stdout.write(self.style.SUCCESS("Done!"))
