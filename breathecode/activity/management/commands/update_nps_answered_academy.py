import os

from django.core.management.base import BaseCommand
from google.auth.exceptions import DefaultCredentialsError
from google.cloud import bigquery

from breathecode.activity.models import ACTIVITY_TABLE_NAME
from breathecode.feedback.models import Survey
from breathecode.services.google_cloud.big_query import BigQuery


class Command(BaseCommand):
    help = "Update nps_answered activities with null academy using the related survey"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Show what would be updated without making changes")

    def _get_mock_results(self):
        """Return sample data for dry-run without credentials"""
        # Find some real surveys from Django to simulate
        surveys = Survey.objects.filter(cohort__academy__isnull=False).select_related("cohort__academy")[:10]

        # Create mock results
        class MockRow:
            def __init__(self, activity_id, survey_id, answer_id=None):
                self.id = activity_id
                self.survey_id = survey_id
                self.answer_id = answer_id

        results = []
        for i, survey in enumerate(surveys):
            # Generate a mock activity ID
            activity_id = f"mock_activity_{i+1}_{survey.id}"
            results.append(MockRow(activity_id, survey.id))

        return results

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        use_mock_data = False

        try:
            client, project_id, dataset = BigQuery.client()
        except DefaultCredentialsError:
            if dry_run:
                # In dry-run, use sample data
                self.stdout.write(
                    self.style.WARNING(
                        "\n⚠️  Google Cloud credentials not found.\n" "Using sample data for dry-run...\n"
                    )
                )
                use_mock_data = True
                project_id = os.getenv("GOOGLE_PROJECT_ID", "test-project")
                dataset = os.getenv("BIGQUERY_DATASET", "test_dataset")
                client = None
            else:
                self.stdout.write(
                    self.style.ERROR(
                        "\n❌ Error: Google Cloud credentials not found.\n\n"
                        "Please configure one of these options:\n"
                        "1. GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json\n"
                        "2. GOOGLE_SERVICE_KEY='{...}' (service account JSON content)\n\n"
                        "You also need:\n"
                        "- GOOGLE_PROJECT_ID=your-project-id\n"
                        "- BIGQUERY_DATASET=dataset-name\n"
                    )
                )
                return

        if not project_id or project_id == "test":
            project_id = project_id or "test-project"
            if not dry_run:
                self.stdout.write(
                    self.style.WARNING(
                        "⚠️  GOOGLE_PROJECT_ID is not configured or is 'test'. "
                        "Make sure to configure environment variables correctly."
                    )
                )

        if not dataset:
            dataset = dataset or "test_dataset"
            if not dry_run:
                self.stdout.write(
                    self.style.WARNING(
                        "⚠️  BIGQUERY_DATASET is not configured. " "Make sure to configure this environment variable."
                    )
                )

        table = f"`{project_id}.{dataset}.{ACTIVITY_TABLE_NAME}`"
        table_ref = f"{project_id}.{dataset}.{ACTIVITY_TABLE_NAME}"

        # Get the actual schema to know which fields exist in meta STRUCT
        # Fallback to common fields if schema fetch fails
        default_meta_fields = [
            "id",
            "title",
            "lowest",
            "highest",
            "lang",
            "score",
            "comment",
            "status",
            "user_email",
            "user_username",
            "user_first_name",
            "user_last_name",
            "mentor_email",
            "mentor_username",
            "mentor_first_name",
            "mentor_last_name",
            "academy",
            "cohort",
            "survey",
            "event",
            "opened_at",
            "sent_at",
        ]
        meta_fields = default_meta_fields.copy()

        if not use_mock_data and client:
            try:
                table_obj = client.get_table(table_ref)
                for field in table_obj.schema:
                    if field.name == "meta" and field.field_type == bigquery.enums.SqlTypeNames.STRUCT:
                        meta_fields = [f.name for f in field.fields]
                        self.stdout.write(
                            f"Found {len(meta_fields)} fields in meta STRUCT: {', '.join(meta_fields[:10])}..."
                        )
                        break
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"⚠️  Could not fetch table schema: {e}. Using default fields."))

        # Get results
        if use_mock_data:
            results = self._get_mock_results()
            self.stdout.write(
                self.style.WARNING(f"📝 Simulation mode: using {len(results)} sample activities from Django\n")
            )
        else:
            # Find activities with academy null
            query = f"""
                SELECT id, SAFE_CAST(meta.survey AS INT64) AS survey_id, SAFE_CAST(meta.id AS INT64) AS answer_id
                FROM {table}
                WHERE kind = 'nps_answered'
                  AND meta.academy IS NULL
                  AND meta.survey IS NOT NULL
            """

            try:
                results = list(client.query(query).result())
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"\n❌ Error querying BigQuery: {str(e)}\n"
                        "Verify that:\n"
                        "- Credentials are correct\n"
                        "- Project and dataset exist\n"
                        "- You have permissions to read the table"
                    )
                )
                return

        if not results:
            self.stdout.write(self.style.SUCCESS("No activities to update"))
            return

        self.stdout.write(f"Found {len(results)} activities")

        # Map survey_id -> academy_id
        survey_ids = {r.survey_id for r in results if r.survey_id}
        self.stdout.write(f"Survey IDs: {survey_ids}")
        surveys = Survey.objects.filter(id__in=survey_ids).select_related("cohort__academy")
        survey_academy = {s.id: s.cohort.academy.id for s in surveys if s.cohort and s.cohort.academy}

        # Update each activity
        updated = 0
        skipped = 0
        for row in results:
            academy_id = survey_academy.get(row.survey_id)
            if not academy_id:
                skipped += 1
                continue

            if dry_run:
                answer_info = f" (Answer {row.answer_id})" if row.answer_id else ""
                self.stdout.write(f"[DRY RUN] Activity {row.id}{answer_info} -> academy {academy_id}")
                updated += 1
                continue

            # UPDATE with explicit STRUCT reconstruction using only fields that exist
            struct_fields = []
            for field_name in meta_fields:
                if field_name == "academy":
                    struct_fields.append("@academy AS academy")
                else:
                    struct_fields.append(f"meta.{field_name}")

            if not struct_fields:
                self.stdout.write(self.style.ERROR(f"Error on {row.id}: No fields found in meta STRUCT"))
                continue

            update_sql = f"""
                UPDATE {table}
                SET meta = STRUCT(
                    {', '.join(struct_fields)}
                )
                WHERE id = @id AND kind = 'nps_answered'
            """

            params = [
                bigquery.ScalarQueryParameter("id", "STRING", row.id),
                bigquery.ScalarQueryParameter("academy", "INT64", academy_id),
            ]

            try:
                client.query(update_sql, job_config=bigquery.QueryJobConfig(query_parameters=params)).result()
                updated += 1
                if updated % 50 == 0:
                    self.stdout.write(f"Updated {updated}...")
            except Exception as e:
                error_msg = str(e)
                if "streaming buffer" in error_msg.lower():
                    self.stdout.write(
                        self.style.WARNING(
                            f"Skipped {row.id}: Still in streaming buffer. "
                            "Will be processed in next run (records must be >2 hours old)."
                        )
                    )
                    skipped += 1
                else:
                    self.stdout.write(self.style.ERROR(f"Error on {row.id}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"\nTotal updated: {updated}"))
        if skipped > 0:
            self.stdout.write(self.style.WARNING(f"Skipped (no academy): {skipped}"))
