from django.core.management.base import BaseCommand

from breathecode.feedback.models import SurveyResponse, SurveyStudy
from breathecode.feedback.tasks import send_survey_response_email


class Command(BaseCommand):
    help = "Schedule sending SurveyResponse emails for all pending responses in a SurveyStudy"

    def add_arguments(self, parser):
        parser.add_argument("--study-id", type=int, required=True, help="SurveyStudy id")
        parser.add_argument(
            "--commit",
            action="store_true",
            help="Enqueue celery tasks (otherwise dry-run)",
        )
        parser.add_argument(
            "--only-missing-email-open",
            action="store_true",
            help="Only schedule if email_opened_at is null (avoid re-sends)",
        )

    def handle(self, *args, **options):
        study_id = options["study_id"]
        commit = options["commit"]
        only_missing_email_open = options["only_missing_email_open"]

        if not commit:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No tasks will be scheduled (use --commit)\n"))

        study = SurveyStudy.objects.filter(id=study_id).first()
        if not study:
            self.stdout.write(self.style.ERROR("SurveyStudy not found"))
            return

        qs = SurveyResponse.objects.filter(survey_study=study).exclude(status=SurveyResponse.Status.ANSWERED)
        if only_missing_email_open:
            qs = qs.filter(email_opened_at__isnull=True)

        ids = list(qs.values_list("id", flat=True))
        total = len(ids)
        if total == 0:
            self.stdout.write(self.style.SUCCESS("No SurveyResponses to schedule"))
            return

        if commit:
            for response_id in ids:
                send_survey_response_email.delay(response_id)

        self.stdout.write(self.style.MIGRATE_HEADING("\n=== Summary ==="))
        self.stdout.write(f"study_id={study_id}")
        self.stdout.write(f"responses_matched={total}")
        self.stdout.write("scheduled=%s" % (total if commit else 0))


