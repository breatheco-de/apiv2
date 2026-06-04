from django.core.management.base import BaseCommand, CommandError

from breathecode.admissions.diagnostics import build_graduation_diagnostic
from breathecode.admissions.models import CohortUser
from breathecode.authenticate.models import User


class Command(BaseCommand):
    help = "Diagnose why a CohortUser did not change to GRADUATED status"

    def add_arguments(self, parser):
        parser.add_argument(
            "--cohort-user-id",
            type=int,
            help="CohortUser ID to diagnose",
        )
        parser.add_argument(
            "--user-id",
            type=int,
            help="User ID to diagnose",
        )
        parser.add_argument(
            "--user-email",
            type=str,
            help="User email to diagnose",
        )
        parser.add_argument(
            "--cohort-id",
            type=int,
            help="Cohort ID (optional, to filter if user is in multiple cohorts)",
        )
        parser.add_argument(
            "--force-graduate",
            action="store_true",
            help="Force graduation if all conditions are met (simulates the receiver)",
        )

    def handle(self, *args, **options):
        cohort_user = None
        user = None
        cohort = None

        if options.get("cohort_user_id"):
            cohort_user = CohortUser.objects.filter(id=options["cohort_user_id"]).first()
            if not cohort_user:
                raise CommandError(f"CohortUser with ID {options['cohort_user_id']} not found")
            user = cohort_user.user
            cohort = cohort_user.cohort

        elif options.get("user_id") or options.get("user_email"):
            if options.get("user_id"):
                user = User.objects.filter(id=options["user_id"]).first()
                if not user:
                    raise CommandError(f"User with ID {options['user_id']} not found")
            else:
                user = User.objects.filter(email=options["user_email"]).first()
                if not user:
                    raise CommandError(f"User with email {options['user_email']} not found")

            query = {"user": user}
            if options.get("cohort_id"):
                query["cohort__id"] = options["cohort_id"]

            cohort_user = CohortUser.objects.filter(**query).exclude(cohort__stage="DELETED").first()
            if not cohort_user:
                raise CommandError(f"CohortUser not found for user {user.email} (ID: {user.id})")
            cohort = cohort_user.cohort

        else:
            raise CommandError("You must provide --cohort-user-id, --user-id, or --user-email")

        result = build_graduation_diagnostic(cohort_user)

        self.stdout.write("=" * 60)
        self.stdout.write(f"Diagnosing graduation for user: {user.email} (ID: {user.id})")
        self.stdout.write(f"CohortUser ID: {cohort_user.id}")
        self.stdout.write("=" * 60)
        self.stdout.write("")
        self.stdout.write("-" * 60)
        self.stdout.write(f"Cohort: {cohort.name} (ID: {cohort.id})")
        self.stdout.write("-" * 60)

        if result.get("already_graduated"):
            self.stdout.write(self.style.SUCCESS(f"✓ User is already GRADUATED"))
            return

        self.stdout.write(f"Summary: {result.get('summary', '')}")
        self.stdout.write("")
        for ch in result.get("checks", []):
            sym = "✓" if ch.get("ok") else ("⚠" if ch.get("severity") == "warning" else "❌")
            self.stdout.write(f"{sym} [{ch.get('slug')}] {ch.get('message')}")

        if result.get("mandatory_projects"):
            mp = result["mandatory_projects"]
            if len(mp) <= 10:
                self.stdout.write(f"  Mandatory projects: {', '.join(mp)}")
            else:
                self.stdout.write(f"  First 10 mandatory projects: {', '.join(mp[:10])}...")

        for sample in result.get("pending_task_samples", []):
            self.stdout.write(
                f"    - {sample.get('associated_slug')}: status={sample.get('task_status')}, "
                f"revision_status={sample.get('revision_status')}"
            )

        for w in result.get("warnings", []):
            self.stdout.write(self.style.WARNING(f"⚠ {w}"))

        issues = result.get("issues", [])
        self.stdout.write("")
        self.stdout.write("=" * 60)
        self.stdout.write("SUMMARY")
        self.stdout.write("=" * 60)

        if len(issues) == 0 and result.get("conditions_met_but_not_graduated"):
            self.stdout.write(
                self.style.WARNING(
                    "⚠ All conditions are met, but user is NOT GRADUATED. "
                    "This likely means the receiver didn't trigger when tasks were approved."
                )
            )
            for line in result.get("possible_reasons_if_stuck", []):
                self.stdout.write(f"  - {line}")
            if options.get("force_graduate"):
                self.stdout.write("")
                self.stdout.write("=" * 60)
                self.stdout.write("FORCING GRADUATION...")
                self.stdout.write("=" * 60)
                before_status = cohort_user.educational_status
                cohort_user.educational_status = "GRADUATED"
                cohort_user.save()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ GRADUATION FORCED: educational_status changed from {before_status} to GRADUATED"
                    )
                )
        elif len(issues) == 0:
            self.stdout.write(
                self.style.SUCCESS(
                    "✓ All checks passed! The receiver should trigger when a task's revision_status is updated."
                )
            )
        else:
            if options.get("force_graduate"):
                self.stdout.write(
                    self.style.ERROR(
                        "❌ Cannot force graduation: There are issues preventing graduation. "
                        "Please fix them first."
                    )
                )
            self.stdout.write(self.style.ERROR(f"❌ Found {len(issues)} issue(s) preventing graduation:"))
            for i, issue in enumerate(issues, 1):
                self.stdout.write(f"  {i}. {issue}")

        self.stdout.write("")
        self.stdout.write(
            "Note: The receiver 'mark_saas_student_as_graduated' triggers when "
            "revision_status is updated, cohort is SaaS, syllabus has mandatory projects, "
            "and there are no pending mandatory tasks."
        )
