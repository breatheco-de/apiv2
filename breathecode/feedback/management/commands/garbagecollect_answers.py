from django.core.management.base import BaseCommand
from breathecode.admissions.models import CohortUser
from breathecode.feedback.models import Answer, Survey
from django.utils import timezone
from datetime import timedelta


class Command(BaseCommand):
    help = "Remove invalid answers keeping the survey answered"

    def remove_questions_from_inactive_students(self):
        """Remove answers from students that are not active or graduated in the cohort"""

        for survey in Survey.objects.filter():
            # prevent remove answers was answered or opened
            pending_answers = Answer.objects.filter(survey=survey, cohort=survey.cohort).exclude(
                status__in=["ANSWERED", "OPENED"]
            )

            user_ids = {x.user.id for x in pending_answers}
            for user_id in user_ids:
                # if the student is not active or graduate, remove all the answers related to this cohort
                if (
                    CohortUser.objects.filter(user__id=user_id, cohort=survey.cohort)
                    .exclude(educational_status__in=["ACTIVE", "GRADUATED"])
                    .exists()
                ):
                    pending_answers.filter(user__id=user_id).delete()

        self.stdout.write(self.style.SUCCESS("Successfully removed invalid survey answers"))

    def remove_old_answers(self):
        """Remove answers that were sent more than 15 days ago"""
        # Calculate the cutoff date (15 days ago)
        cutoff_date = timezone.now() - timedelta(days=15)

        # Get answers older than 15 days that were sent but not answered
        old_answers = Answer.objects.filter(sent_at__lt=cutoff_date, status__in=["SENT", "OPENED", "PENDING"])

        deleted_count = old_answers.count()
        old_answers.delete()

        self.stdout.write(self.style.SUCCESS(f"Successfully removed {deleted_count} old survey answers"))

    def remove_expired_survey_answers(self):
        """Remove answers from surveys that have expired based on their duration"""
        from django.utils import timezone

        # Get all surveys that have been sent
        surveys = Survey.objects.filter(sent_at__isnull=False)
        total_deleted = 0

        for survey in surveys:
            # Calculate expiration time based on sent_at + duration
            expiration_time = survey.sent_at + survey.duration

            # If survey is expired
            if expiration_time < timezone.now():
                # Get all non-answered answers for this survey
                expired_answers = Answer.objects.filter(survey=survey, status__in=["SENT", "OPENED", "PENDING"])

                count = expired_answers.count()
                expired_answers.delete()
                total_deleted += count

        if total_deleted > 0:
            self.stdout.write(self.style.SUCCESS(f"Successfully removed {total_deleted} expired survey answers"))

    def handle(self, *args, **options):
        """Execute garbage collection tasks"""
        self.remove_questions_from_inactive_students()
        self.remove_old_answers()
        self.remove_expired_survey_answers()
        self.stdout.write(self.style.SUCCESS("Successfully completed garbage collection"))
