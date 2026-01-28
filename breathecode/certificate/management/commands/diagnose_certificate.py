from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from breathecode.admissions.models import Cohort, CohortUser, FULLY_PAID, UP_TO_DATE
from breathecode.authenticate.models import User
from breathecode.certificate.actions import how_many_pending_tasks
from breathecode.certificate.models import LayoutDesign, Specialty, UserSpecialty


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

        # If --all-graduated is provided, find all graduated users without certificates
        if all_graduated:
            self.find_and_diagnose_all_graduated(academy_id, limit)
            return

        # If cohort_user_id is provided, use it directly
        if cohort_user_id:
            try:
                cohort_user = CohortUser.objects.exclude(cohort__stage="DELETED").get(id=cohort_user_id)
                user = cohort_user.user
                cohort_users = [cohort_user]
            except CohortUser.DoesNotExist:
                raise CommandError(f"CohortUser with id {cohort_user_id} does not exist")
        elif user_id or user_email:
            if not user_id and not user_email:
                raise CommandError("You must provide either --cohort-user-id, --user-id, or --user-email")

            # Get user
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

            # Get CohortUser
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

        # Use the diagnose_cohort_user method for each cohort_user
        user = cohort_users[0].user
        self.stdout.write(self.style.SUCCESS(f"\n{'='*60}"))
        self.stdout.write(self.style.SUCCESS(f"Diagnosing certificate for user: {user.email} (ID: {user.id})"))
        if cohort_user_id:
            self.stdout.write(self.style.SUCCESS(f"CohortUser ID: {cohort_user_id}"))
        self.stdout.write(self.style.SUCCESS(f"{'='*60}\n"))

        for cohort_user in cohort_users:
            self.diagnose_cohort_user(cohort_user)

    def find_and_diagnose_all_graduated(self, academy_id=None, limit=None):
        """
        Find all graduated users without certificates and diagnose them.
        """
        self.stdout.write(self.style.SUCCESS(f"\n{'='*60}"))
        self.stdout.write(self.style.SUCCESS("Buscando usuarios graduados sin certificado..."))
        self.stdout.write(self.style.SUCCESS(f"{'='*60}\n"))

        # Find all CohortUser with educational_status="GRADUATED"
        query = {
            "educational_status": "GRADUATED",
            "role": "STUDENT",
        }
        
        # Exclude deleted cohorts
        cohort_users = CohortUser.objects.filter(**query).exclude(cohort__stage="DELETED")
        
        # Filter by academy if provided
        if academy_id:
            cohort_users = cohort_users.filter(cohort__academy__id=academy_id)
        
        # Get users that don't have a PERSISTED certificate for their cohort
        # Only for cohorts with available_as_saas=True (consistent with receiver)
        graduated_without_cert = []
        for cohort_user in cohort_users.select_related("user", "cohort", "cohort__academy"):
            # Check if cohort is available as SaaS (consistent with receiver)
            if not cohort_user.cohort.available_as_saas:
                continue
            
            # Check if user has a PERSISTED certificate for this cohort
            has_certificate = UserSpecialty.objects.filter(
                user=cohort_user.user,
                cohort=cohort_user.cohort,
                status="PERSISTED"
            ).exists()
            
            if not has_certificate:
                graduated_without_cert.append(cohort_user)
        
        total_found = len(graduated_without_cert)
        self.stdout.write(
            self.style.SUCCESS(f"Encontrados {total_found} usuarios graduados sin certificado")
        )
        
        if limit:
            graduated_without_cert = graduated_without_cert[:limit]
            self.stdout.write(
                self.style.WARNING(f"Limitando a {limit} usuarios (de {total_found} encontrados)")
            )
        
        if not graduated_without_cert:
            self.stdout.write(self.style.SUCCESS("\n✓ No se encontraron usuarios graduados sin certificado"))
            return
        
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(f"Diagnosticando {len(graduated_without_cert)} usuarios...")
        self.stdout.write(f"{'='*60}\n")
        
        # Group by user to avoid duplicate diagnoses
        users_processed = set()
        for cohort_user in graduated_without_cert:
            user_key = (cohort_user.user.id, cohort_user.cohort.id)
            if user_key in users_processed:
                continue
            users_processed.add(user_key)
            
            # Diagnose this specific cohort_user
            self.diagnose_cohort_user(cohort_user)
        
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(
            self.style.SUCCESS(f"✓ Diagnóstico completado para {len(users_processed)} usuarios")
        )
        self.stdout.write(f"{'='*60}\n")

    def diagnose_cohort_user(self, cohort_user):
        """
        Diagnose a specific CohortUser and print the results.
        """
        user = cohort_user.user
        cohort = cohort_user.cohort
        
        self.stdout.write(f"\n{'='*80}")
        self.stdout.write(
            self.style.SUCCESS(
                f"Usuario: {user.email} (ID: {user.id}) | "
                f"Cohort: {cohort.name} (ID: {cohort.id}) | "
                f"Academia: {cohort.academy.name if cohort.academy else 'N/A'}"
            )
        )
        self.stdout.write(f"{'='*80}\n")
        
        issues = []
        warnings = []
        
        # Check 1: CohortUser exists
        self.stdout.write("✓ CohortUser exists")
        
        # Check 2: Cohort has syllabus_version
        if cohort.syllabus_version is None:
            issues.append("Cohort has no syllabus_version assigned")
            self.stdout.write(self.style.ERROR("❌ Cohort has no syllabus_version assigned"))
        else:
            self.stdout.write(f"✓ Cohort has syllabus_version: {cohort.syllabus_version.syllabus.name}")
        
        # Check 3: Specialty exists
        if cohort.syllabus_version:
            specialty = Specialty.objects.filter(syllabus__id=cohort.syllabus_version.syllabus_id).first()
            if not specialty:
                issues.append("Specialty has no Syllabus assigned")
                self.stdout.write(self.style.ERROR("❌ Specialty has no Syllabus assigned"))
            else:
                self.stdout.write(f"✓ Specialty exists: {specialty.name}")
        
        # Check 4: Certificate already exists
        uspe = UserSpecialty.objects.filter(user=user, cohort=cohort).first()
        if uspe is not None and uspe.status == "PERSISTED" and uspe.preview_url:
            self.stdout.write(
                self.style.WARNING(
                    f"⚠️  User already has a certificate created (Status: {uspe.status}, ID: {uspe.id})"
                )
            )
        elif uspe is not None:
            self.stdout.write(
                self.style.WARNING(
                    f"⚠️  UserSpecialty exists but not persisted (Status: {uspe.status}, ID: {uspe.id})"
                )
            )
        else:
            self.stdout.write("✓ No existing certificate found")
        
        # Check 5: Layout exists
        layout = LayoutDesign.objects.filter(is_default=True, academy=cohort.academy).first()
        if layout is None:
            layout = LayoutDesign.objects.filter(slug="default").first()
        if layout is None:
            issues.append("No layout found (no default layout for academy and no 'default' layout)")
            self.stdout.write(
                self.style.ERROR("❌ No layout found (no default layout for academy and no 'default' layout)")
            )
        else:
            self.stdout.write(f"✓ Layout found: {layout.name} (slug: {layout.slug})")
        
        # Check 6: Main teacher exists
        main_teacher = CohortUser.objects.filter(cohort__id=cohort.id, role="TEACHER").first()
        if main_teacher is None or main_teacher.user is None:
            issues.append("Cohort does not have a main teacher")
            self.stdout.write(self.style.ERROR("❌ Cohort does not have a main teacher"))
        else:
            self.stdout.write(
                f"✓ Main teacher exists: {main_teacher.user.first_name} {main_teacher.user.last_name}"
            )
        
        # Check 7: Pending tasks
        if cohort.syllabus_version:
            try:
                pending_tasks = how_many_pending_tasks(
                    cohort.syllabus_version,
                    user,
                    task_types=["PROJECT"],
                    only_mandatory=True,
                    cohort_id=cohort.id,
                )
                if pending_tasks and pending_tasks > 0:
                    issues.append(f"User has {pending_tasks} pending mandatory PROJECT tasks")
                    self.stdout.write(
                        self.style.ERROR(f"❌ User has {pending_tasks} pending mandatory PROJECT tasks")
                    )
                else:
                    self.stdout.write("✓ No pending mandatory PROJECT tasks")
            except Exception as e:
                warnings.append(f"Could not check pending tasks: {str(e)}")
                self.stdout.write(self.style.WARNING(f"⚠️  Could not check pending tasks: {str(e)}"))
        
        # Check 8: Financial status
        if not (cohort_user.finantial_status == FULLY_PAID or cohort_user.finantial_status == UP_TO_DATE):
            issues.append(
                f"Financial status is '{cohort_user.finantial_status}' (must be FULLY_PAID or UP_TO_DATE)"
            )
            self.stdout.write(
                self.style.ERROR(
                    f"❌ Financial status is '{cohort_user.finantial_status}' (must be FULLY_PAID or UP_TO_DATE)"
                )
            )
        else:
            self.stdout.write(f"✓ Financial status is OK: {cohort_user.finantial_status}")
        
        # Check 9: Educational status
        if cohort_user.educational_status != "GRADUATED":
            issues.append(
                f"Educational status is '{cohort_user.educational_status}' (must be GRADUATED)"
            )
            self.stdout.write(
                self.style.ERROR(
                    f"❌ Educational status is '{cohort_user.educational_status}' (must be GRADUATED)"
                )
            )
        else:
            self.stdout.write(f"✓ Educational status is OK: {cohort_user.educational_status}")
        
        # Check 10: Cohort stage and current_day
        if cohort.never_ends:
            self.stdout.write("✓ Cohort never_ends is True (skipping current_day check)")
        else:
            if cohort.syllabus_version:
                expected_days = cohort.syllabus_version.syllabus.duration_in_days
                if cohort.current_day != expected_days:
                    issues.append(
                        f"Cohort current_day is {cohort.current_day} (expected {expected_days})"
                    )
                    self.stdout.write(
                        self.style.ERROR(
                            f"❌ Cohort current_day is {cohort.current_day} (expected {expected_days})"
                        )
                    )
                else:
                    self.stdout.write(f"✓ Cohort current_day is correct: {cohort.current_day}")
            
            if cohort.stage != "ENDED":
                issues.append(f"Cohort stage is '{cohort.stage}' (must be ENDED)")
                self.stdout.write(
                    self.style.ERROR(f"❌ Cohort stage is '{cohort.stage}' (must be ENDED)")
                )
            else:
                self.stdout.write(f"✓ Cohort stage is OK: {cohort.stage}")
        
        # Summary for this user
        self.stdout.write(f"\n{'─'*80}")
        if issues:
            self.stdout.write(self.style.ERROR(f"❌ ISSUES FOUND ({len(issues)}):"))
            for i, issue in enumerate(issues, 1):
                self.stdout.write(self.style.ERROR(f"  {i}. {issue}"))
        else:
            self.stdout.write(self.style.SUCCESS("✓ All checks passed! Certificate should be generable."))
        
        if warnings:
            self.stdout.write(self.style.WARNING(f"⚠️  WARNINGS ({len(warnings)}):"))
            for i, warning in enumerate(warnings, 1):
                self.stdout.write(self.style.WARNING(f"  {i}. {warning}"))
        self.stdout.write(f"{'─'*80}\n")

