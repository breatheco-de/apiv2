from django.core.management.base import BaseCommand
from django.db.models import Count

from breathecode.admissions.models import Cohort, CohortUser


class Command(BaseCommand):
    help = "Sync users from main cohorts to their micro-cohorts with the same role"

    def handle(self, *args, **options):
        # Get all cohorts that have micro-cohorts
        main_cohorts = Cohort.objects.annotate(micro_cohort_count=Count("micro_cohorts")).filter(
            micro_cohort_count__gt=0
        )

        self.stdout.write(f"Found {main_cohorts.count()} main cohorts with micro-cohorts")

        for main_cohort in main_cohorts:
            self.stdout.write(f"\nProcessing main cohort: {main_cohort.name}")

            # Get all users from the main cohort
            main_cohort_users = CohortUser.objects.filter(cohort=main_cohort)

            # Get all micro-cohorts for this main cohort
            micro_cohorts = main_cohort.micro_cohorts.all()

            self.stdout.write(f"Found {main_cohort_users.count()} users in main cohort")
            self.stdout.write(f"Found {micro_cohorts.count()} micro-cohorts")

            # For each user in the main cohort
            for cohort_user in main_cohort_users:
                self.stdout.write(f"\nProcessing user: {cohort_user.user.email}")

                # For each micro-cohort
                for micro_cohort in micro_cohorts:
                    # Check if user exists in micro-cohort with same role
                    exists = CohortUser.objects.filter(
                        cohort=micro_cohort, user=cohort_user.user, role=cohort_user.role
                    ).exists()

                    if not exists:
                        # Create new CohortUser for micro-cohort
                        CohortUser.objects.create(
                            user=cohort_user.user,
                            cohort=micro_cohort,
                            role=cohort_user.role,
                            educational_status=cohort_user.educational_status,
                            finantial_status=cohort_user.finantial_status,
                            watching=cohort_user.watching,
                        )
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"Added user {cohort_user.user.email} to micro-cohort {micro_cohort.name} "
                                f"with role {cohort_user.role}"
                            )
                        )
                    else:
                        self.stdout.write(
                            f"User {cohort_user.user.email} already exists in micro-cohort {micro_cohort.name}"
                        )

        self.stdout.write(self.style.SUCCESS("\nSuccessfully synced users to micro-cohorts"))
