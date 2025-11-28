from django.core.management.base import BaseCommand, CommandError

from breathecode.admissions.models import Cohort, CohortUser
from breathecode.authenticate.models import User
from breathecode.certificate.actions import get_assets_from_syllabus, how_many_pending_tasks
from breathecode.assignments.models import Task


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

        # Get CohortUser
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

        self.stdout.write("=" * 60)
        self.stdout.write(f"Diagnosing graduation for user: {user.email} (ID: {user.id})")
        self.stdout.write(f"CohortUser ID: {cohort_user.id}")
        self.stdout.write("=" * 60)
        self.stdout.write("")
        self.stdout.write("-" * 60)
        self.stdout.write(f"Cohort: {cohort.name} (ID: {cohort.id})")
        self.stdout.write("-" * 60)

        issues = []

        # Check 1: Current educational status
        self.stdout.write(f"Current educational_status: {cohort_user.educational_status}")
        if cohort_user.educational_status == "GRADUATED":
            self.stdout.write(self.style.SUCCESS("✓ User is already GRADUATED"))
            return
        else:
            self.stdout.write(
                self.style.WARNING(f"⚠ User is not GRADUATED (current: {cohort_user.educational_status})")
            )

        # Check 2: Cohort is SaaS
        if not cohort.available_as_saas:
            issues.append("Cohort is not available_as_saas (must be True for automatic graduation)")
            self.stdout.write(
                self.style.ERROR(f"❌ Cohort available_as_saas is {cohort.available_as_saas} (must be True)")
            )
        else:
            self.stdout.write(f"✓ Cohort available_as_saas: {cohort.available_as_saas}")

        # Check 3: Cohort has syllabus_version
        if not cohort.syllabus_version:
            issues.append("Cohort has no syllabus_version")
            self.stdout.write(self.style.ERROR("❌ Cohort has no syllabus_version"))
            return
        else:
            self.stdout.write(f"✓ Cohort has syllabus_version: {cohort.syllabus_version.syllabus.name}")

        # Check 4: Syllabus has mandatory projects
        mandatory_projects = get_assets_from_syllabus(
            cohort.syllabus_version, task_types=["PROJECT"], only_mandatory=True
        )
        if len(mandatory_projects) == 0:
            issues.append("Syllabus has no mandatory projects (automatic graduation requires mandatory projects)")
            self.stdout.write(
                self.style.ERROR(f"❌ Syllabus has no mandatory projects (found {len(mandatory_projects)} projects)")
            )
        else:
            self.stdout.write(f"✓ Syllabus has {len(mandatory_projects)} mandatory projects")
            if len(mandatory_projects) <= 10:
                self.stdout.write(f"  Projects: {', '.join(mandatory_projects)}")
            else:
                self.stdout.write(f"  First 10 projects: {', '.join(mandatory_projects[:10])}...")

        # Check 5: Pending mandatory tasks
        pending_tasks = how_many_pending_tasks(
            cohort.syllabus_version,
            user,
            task_types=["PROJECT"],
            only_mandatory=True,
            cohort_id=cohort.id,
        )
        if pending_tasks > 0:
            issues.append(f"User has {pending_tasks} pending mandatory PROJECT tasks")
            self.stdout.write(
                self.style.ERROR(f"❌ User has {pending_tasks} pending mandatory PROJECT tasks")
            )

            # Show which tasks are pending
            user_tasks = Task.objects.filter(
                user=user, associated_slug__in=mandatory_projects, cohort=cohort
            ).exclude(revision_status__in=["APPROVED", "IGNORED"])

            self.stdout.write("  Pending tasks:")
            for task in user_tasks[:10]:  # Show first 10
                self.stdout.write(
                    f"    - {task.associated_slug}: status={task.task_status}, "
                    f"revision_status={task.revision_status}"
                )
            if user_tasks.count() > 10:
                self.stdout.write(f"    ... and {user_tasks.count() - 10} more")
        else:
            self.stdout.write(f"✓ No pending mandatory PROJECT tasks (pending: {pending_tasks})")

        # Check 6: Financial status (blocks manual graduation)
        if cohort_user.finantial_status == "LATE":
            issues.append("Financial status is LATE (blocks manual graduation via API)")
            self.stdout.write(
                self.style.ERROR(f"❌ Financial status is LATE (blocks manual graduation via API)")
            )
        else:
            self.stdout.write(f"✓ Financial status: {cohort_user.finantial_status}")

        # Check 7: Task status changes (receiver trigger)
        # Check if there are any tasks that should have triggered the receiver
        user_tasks_all = Task.objects.filter(user=user, cohort=cohort, task_type="PROJECT")
        tasks_with_revision = user_tasks_all.exclude(revision_status__in=["", None])
        
        # Get detailed task info for summary
        approved_tasks = None
        all_tasks_approved = False
        
        if tasks_with_revision.count() == 0:
            self.stdout.write(
                self.style.WARNING(
                    "⚠ No PROJECT tasks with revision_status found (receiver triggers on revision_status_updated)"
                )
            )
        else:
            self.stdout.write(
                f"✓ Found {tasks_with_revision.count()} PROJECT tasks with revision_status"
            )
            
            # Show detailed task status
            approved_tasks = tasks_with_revision.filter(revision_status="APPROVED")
            pending_tasks_list = tasks_with_revision.exclude(revision_status__in=["APPROVED", "IGNORED"])
            
            self.stdout.write(f"  - Approved: {approved_tasks.count()}")
            self.stdout.write(f"  - Pending/Other: {pending_tasks_list.count()}")
            
            # Check if all mandatory tasks are approved
            mandatory_tasks = user_tasks_all.filter(associated_slug__in=mandatory_projects)
            all_tasks_approved = (
                mandatory_tasks.exclude(revision_status__in=["APPROVED", "IGNORED"]).count() == 0
                and mandatory_tasks.filter(revision_status="APPROVED").count() > 0
            )
            
            # Check when tasks were last updated
            if approved_tasks.exists():
                last_updated = approved_tasks.order_by("-updated_at").first()
                if last_updated:
                    self.stdout.write(
                        f"  - Last task updated: {last_updated.updated_at} "
                        f"(task: {last_updated.associated_slug}, status: {last_updated.revision_status})"
                    )
            
            # IMPORTANT: Explain the issue
            if pending_tasks == 0 and approved_tasks.count() > 0:
                self.stdout.write("")
                self.stdout.write(
                    self.style.WARNING(
                        "⚠ IMPORTANT: The receiver 'mark_saas_student_as_graduated' only triggers "
                        "when a task's revision_status is UPDATED (via signal)."
                    )
                )
                self.stdout.write(
                    "  If all tasks were already approved before the receiver could check, "
                    "or if the receiver didn't run when the last task was approved, "
                    "the user won't be automatically graduated."
                )
                self.stdout.write("")
                self.stdout.write(
                    "  SOLUTION: You can manually trigger graduation by updating any task's "
                    "revision_status, or use the admin action to manually set educational_status to GRADUATED."
                )

        # Summary
        self.stdout.write("")
        self.stdout.write("=" * 60)
        self.stdout.write("SUMMARY")
        self.stdout.write("=" * 60)

        if len(issues) == 0:
            # Check if all tasks are approved but user is still not GRADUATED
            if all_tasks_approved and cohort_user.educational_status != "GRADUATED":
                self.stdout.write(
                    self.style.WARNING(
                        "⚠ All conditions are met, but user is NOT GRADUATED. "
                        "This likely means the receiver didn't trigger when tasks were approved."
                    )
                )
                self.stdout.write("")
                self.stdout.write("POSSIBLE REASONS:")
                self.stdout.write("  1. Tasks were approved before the receiver was implemented")
                self.stdout.write("  2. The receiver didn't run when the last task was approved")
                self.stdout.write("  3. There was an error when the receiver tried to run")
                self.stdout.write("  4. The signal 'revision_status_updated' wasn't sent")
                self.stdout.write("")
                self.stdout.write("SOLUTION:")
                self.stdout.write("  - Option 1: Use --force-graduate to manually graduate the user")
                self.stdout.write("  - Option 2: Manually set educational_status to GRADUATED in admin")
                self.stdout.write(
                    "  - Option 3: Trigger the receiver by updating any task's revision_status "
                    "(even if it's already APPROVED, you can save it again)"
                )
                
                # Force graduation if requested
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
                    self.stdout.write(f"  CohortUser ID: {cohort_user.id}")
                    self.stdout.write(f"  User: {user.email} (ID: {user.id})")
                    self.stdout.write(f"  Cohort: {cohort.name} (ID: {cohort.id})")
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        "✓ All checks passed! The user should be able to graduate. "
                        "The receiver should trigger when a task's revision_status is updated."
                    )
                )
        else:
            if options.get("force_graduate"):
                self.stdout.write("")
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
        self.stdout.write("Note: The receiver 'mark_saas_student_as_graduated' triggers when:")
        self.stdout.write("  1. A task's revision_status is updated (via signal)")
        self.stdout.write("  2. Cohort available_as_saas = True")
        self.stdout.write("  3. Syllabus has mandatory projects")
        self.stdout.write("  4. No pending mandatory tasks")
        self.stdout.write("")
        self.stdout.write("IMPORTANT: The receiver is EVENT-DRIVEN, not state-driven.")
        self.stdout.write("  It only runs when a task's revision_status changes, not when you check the state.")
        self.stdout.write("")
        self.stdout.write("If all conditions are met but user is not GRADUATED, check the logs for:")
        self.stdout.write("  '[graduate]' messages to see what the receiver is doing")

