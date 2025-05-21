import json
import os

from django.core.management.base import BaseCommand

from breathecode.admissions.models import ACTIVE, STUDENT, CohortUser
from breathecode.authenticate.models import ProfileAcademy


class Command(BaseCommand):
    """
    Generate a report of active students grouped by academy, including their ProfileAcademy information.

    This command finds all CohortUser records with:
    - educational_status=ACTIVE
    - role=STUDENT

    Then matches them with ProfileAcademy records having the same user or email,
    and groups the results by academy, counting each student only once per academy.
    """

    help = "Generate a report of active students grouped by academy, including their ProfileAcademy information"

    def add_arguments(self, parser):
        parser.add_argument(
            "--academy",
            type=int,
            help="Filter by academy ID",
        )

        parser.add_argument(
            "--output",
            type=str,
            help="Output file path (default: stdout)",
        )

    def handle(self, *args, **options):
        # Get CohortUsers that are active students
        query = CohortUser.objects.filter(educational_status=ACTIVE, role=STUDENT).select_related(
            "user", "cohort", "cohort__academy"
        )

        # Apply academy filter if provided
        academy_id = options.get("academy")
        if academy_id:
            query = query.filter(cohort__academy__id=academy_id)

        active_student_cohort_users = query

        # Initialize result structure
        academy_reports = {}

        # Track which users have been processed for each academy
        processed_users_by_academy = {}

        # Process each cohort user
        for cohort_user in active_student_cohort_users:
            user = cohort_user.user
            academy = cohort_user.cohort.academy

            # Skip if no user
            if not user:
                continue

            # Initialize academy entry if needed
            if academy.id not in academy_reports:
                academy_reports[academy.id] = {
                    "academy": academy.id,
                    "academy_name": academy.name,
                    "total_students": 0,
                    "students": [],
                }
                processed_users_by_academy[academy.id] = set()

            # Check if this user is already processed for this academy
            if user.id in processed_users_by_academy[academy.id]:
                # User already processed - find their entry and add this cohort
                for student in academy_reports[academy.id]["students"]:
                    if student["user_id"] == user.id:
                        student["cohorts"].append(
                            {
                                "cohort_id": cohort_user.cohort.id,
                                "cohort_name": cohort_user.cohort.name,
                                "cohort_user_id": cohort_user.id,
                                "educational_status": cohort_user.educational_status,
                            }
                        )
                        break
                continue

            # Get the ProfileAcademy for this user at this academy
            profile_academy = ProfileAcademy.objects.filter(academy=academy, user=user).select_related("role").first()

            # If not found by user, try by email
            if profile_academy is None and user.email:
                profile_academy = (
                    ProfileAcademy.objects.filter(academy=academy, email=user.email).select_related("role").first()
                )

            # Skip if no profile academy found
            if profile_academy is None:
                continue

            # This is a new user for this academy
            # Create student info with initial cohort
            student_info = {
                "user_id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "profile_academy_id": profile_academy.id,
                "profile_academy_role": profile_academy.role.slug if profile_academy.role else None,
                "cohorts": [
                    {
                        "cohort_id": cohort_user.cohort.id,
                        "cohort_name": cohort_user.cohort.name,
                        "cohort_user_id": cohort_user.id,
                        "educational_status": cohort_user.educational_status,
                    }
                ],
            }

            # Add to results and mark as processed
            academy_reports[academy.id]["students"].append(student_info)
            academy_reports[academy.id]["total_students"] += 1
            processed_users_by_academy[academy.id].add(user.id)

        # Convert to list for the final output format
        final_report = list(academy_reports.values())

        # Format the report as JSON with indentation
        json_output = json.dumps(final_report, indent=4)

        # Output to file or stdout
        output_path = options.get("output")
        if output_path:
            # Create directory if it doesn't exist
            dir_path = os.path.dirname(os.path.abspath(output_path))
            if dir_path:  # Skip if the output is just a filename in the current directory
                os.makedirs(dir_path, exist_ok=True)

            with open(output_path, "w") as f:
                f.write(json_output)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully generated report with {len(final_report)} academies and saved to {output_path}"
                )
            )
        else:
            # Output to stdout
            self.stdout.write(json_output)
            self.stdout.write(self.style.SUCCESS(f"Successfully generated report with {len(final_report)} academies"))
