from django.core.management.base import BaseCommand
from breathecode.admissions.models import CohortUser
from breathecode.feedback.models import Answer, Survey


class Command(BaseCommand):
    help = "Remove invalid answers keeping the survey answered"

    def handle(self, *args, **options):
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

        self.stdout.write(self.style.SUCCESS("Successfully deleted invalid answers"))
