from django.core.management.base import BaseCommand, CommandError

from breathecode.admissions.models import CohortUser
from breathecode.authenticate.models import User
from breathecode.certificate.diagnostics import (
    build_certificate_diagnostic,
    list_graduated_without_certificate_cohort_users,
)


class Command(BaseCommand):
    help = "Diagnose why a certificate was not generated for a user in a cohort"

    def add_arguments(self, parser):
        parser.add_argument(
            "--cohort-user-id",
            type=int,
            help="CohortUser ID to diagnose (recommended)",
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
            help="Cohort ID (optional, will use first cohort if not provided)",
        )
        parser.add_argument(
            "--all-graduated",
            action="store_true",
            help="Find all graduated users without certificates and diagnose them",
        )
        parser.add_argument(
            "--academy-id",
            type=int,
            help="Filter by academy ID (only used with --all-graduated)",
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Limit the number of users to diagnose (only used with --all-graduated)",
        )

    def handle(self, *args, **options):
        cohort_user_id = options.get("cohort_user_id")
        user_id = options.get("user_id")
        user_email = options.get("user_email")
        cohort_id = options.get("cohort_id")
        all_graduated = options.get("all_graduated", False)
        academy_id = options.get("academy_id")
        limit = options.get("limit")

        if all_graduated:
            self.find_and_diagnose_all_graduated(academy_id, limit)
            return

        if cohort_user_id:
            try:
                cohort_user = CohortUser.objects.exclude(cohort__stage="DELETED").get(id=cohort_user_id)
                cohort_users = [cohort_user]
            except CohortUser.DoesNotExist:
                raise CommandError(f"CohortUser with id {cohort_user_id} does not exist")
        elif user_id or user_email:
            if user_id:
                try:
                    user = User.objects.get(id=user_id)
                except User.DoesNotExist:
                    raise CommandError(f"User with id {user_id} does not exist")
            else:
                try:
                    user = User.objects.get(email=user_email)
                except User.DoesNotExist:
                    raise CommandError(f"User with email {user_email} does not exist")

            query = {"user__id": user.id}
            if cohort_id:
                query["cohort__id"] = cohort_id

            cohort_users = CohortUser.objects.filter(**query).exclude(cohort__stage="DELETED")

            if not cohort_users.exists():
                self.stdout.write(
                    self.style.ERROR("❌ FAILED: No CohortUser found (user is not assigned to any cohort)")
                )
                return

            if cohort_id:
                cohort_users = [cohort_users.first()]
            else:
                if cohort_users.count() > 1:
                    self.stdout.write(
                        self.style.WARNING(
                            f"⚠️  WARNING: User is in {cohort_users.count()} cohorts. Analyzing all of them:\n"
                        )
                    )
                cohort_users = list(cohort_users)
        else:
            raise CommandError("You must provide either --cohort-user-id, --user-id, or --user-email")

        user = cohort_users[0].user
        self.stdout.write(self.style.SUCCESS(f"\n{'='*60}"))
        self.stdout.write(self.style.SUCCESS(f"Diagnosing certificate for user: {user.email} (ID: {user.id})"))
        if cohort_user_id:
            self.stdout.write(self.style.SUCCESS(f"CohortUser ID: {cohort_user_id}"))
        self.stdout.write(self.style.SUCCESS(f"{'='*60}\n"))

        for cohort_user in cohort_users:
            self._print_diagnostic(cohort_user)

    def find_and_diagnose_all_graduated(self, academy_id=None, limit=None):
        self.stdout.write(self.style.SUCCESS(f"\n{'='*60}"))
        self.stdout.write(self.style.SUCCESS("Buscando usuarios graduados sin certificado..."))
        self.stdout.write(self.style.SUCCESS(f"{'='*60}\n"))

        graduated_without_cert = list_graduated_without_certificate_cohort_users(academy_id, limit)

        total_found = len(graduated_without_cert)
        self.stdout.write(self.style.SUCCESS(f"Encontrados {total_found} usuarios graduados sin certificado"))

        if not graduated_without_cert:
            self.stdout.write(self.style.SUCCESS("\n✓ No se encontraron usuarios graduados sin certificado"))
            return

        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(f"Diagnosticando {len(graduated_without_cert)} usuarios...")
        self.stdout.write(f"{'='*60}\n")

        users_processed = set()
        for cohort_user in graduated_without_cert:
            user_key = (cohort_user.user.id, cohort_user.cohort.id)
            if user_key in users_processed:
                continue
            users_processed.add(user_key)
            self._print_diagnostic(cohort_user)

        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(self.style.SUCCESS(f"✓ Diagnóstico completado para {len(users_processed)} usuarios"))
        self.stdout.write(f"{'='*60}\n")

    def _print_diagnostic(self, cohort_user):
        user = cohort_user.user
        cohort = cohort_user.cohort
        result = build_certificate_diagnostic(cohort_user)

        self.stdout.write(f"\n{'='*80}")
        self.stdout.write(
            self.style.SUCCESS(
                f"Usuario: {user.email} (ID: {user.id}) | "
                f"Cohort: {cohort.name} (ID: {cohort.id}) | "
                f"Academia: {cohort.academy.name if cohort.academy else 'N/A'}"
            )
        )
        self.stdout.write(f"{'='*80}\n")

        for ch in result.get("checks", []):
            sym = "✓" if ch.get("ok") else ("⚠" if ch.get("severity") == "warning" else "❌")
            self.stdout.write(f"{sym} [{ch.get('slug')}] {ch.get('message')}")

        mp = result.get("mandatory_project_slugs") or []
        if mp:
            if len(mp) <= 10:
                self.stdout.write(f"\nMandatory PROJECT slugs: {', '.join(mp)}")
            else:
                self.stdout.write(f"\nMandatory PROJECT slugs (first 10): {', '.join(mp[:10])}...")

        for sample in result.get("pending_task_samples") or []:
            self.stdout.write(
                f"    • {sample.get('associated_slug')}: task_status={sample.get('task_status')}, "
                f"revision_status={sample.get('revision_status')}"
            )

        self.stdout.write(f"\n{'─'*80}")
        self.stdout.write(result.get("summary", ""))
        if result.get("issues"):
            self.stdout.write(self.style.ERROR(f"❌ ISSUES FOUND ({len(result['issues'])}):"))
            for i, issue in enumerate(result["issues"], 1):
                self.stdout.write(self.style.ERROR(f"  {i}. {issue}"))
        else:
            self.stdout.write(self.style.SUCCESS("✓ All checks passed! Certificate should be generable."))

        if result.get("warnings"):
            self.stdout.write(self.style.WARNING(f"⚠️  WARNINGS ({len(result['warnings'])}):"))
            for i, warning in enumerate(result["warnings"], 1):
                self.stdout.write(self.style.WARNING(f"  {i}. {warning}"))
        self.stdout.write(f"{'─'*80}\n")
