"""
Management command to generate monitoring reports.

Usage:
    # Generate yesterday's churn report (default)
    python manage.py generate_report churn

    # Generate for specific date
    python manage.py generate_report churn --date 2024-12-15

    # Generate for specific academy
    python manage.py generate_report churn --academy 1

    # Backfill last 30 days
    python manage.py generate_report churn --days-back 30

    # Dry run (test without saving)
    python manage.py generate_report churn --dry-run

    # Verbose output
    python manage.py generate_report churn --verbosity 2
"""

import traceback
from datetime import date, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

# Import all report types
from breathecode.monitoring.reports.churn.actions import ChurnReport

# Registry of available report types
REPORT_REGISTRY = {
    "churn": ChurnReport,
    # Add future reports here:
    # "engagement": EngagementReport,
    # "revenue": RevenueReport,
}


class Command(BaseCommand):
    help = "Generate monitoring reports (churn, engagement, revenue, etc.)"

    def add_arguments(self, parser):
        parser.add_argument(
            "report_type",
            type=str,
            choices=list(REPORT_REGISTRY.keys()),
            help=f"Type of report to generate: {', '.join(REPORT_REGISTRY.keys())}",
        )
        parser.add_argument(
            "--date",
            type=str,
            default=None,
            help="Report date (YYYY-MM-DD). Defaults to yesterday.",
        )
        parser.add_argument(
            "--academy",
            type=int,
            default=None,
            help="Filter by academy ID. Generates for all academies if not specified.",
        )
        parser.add_argument(
            "--days-back",
            type=int,
            default=None,
            help="Generate reports for the last N days (backfill mode).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Fetch and process data but don't save to database.",
        )

    def handle(self, *args, **options):
        report_type = options["report_type"]
        academy_id = options.get("academy")
        dry_run = options.get("dry_run", False)
        verbosity = options.get("verbosity", 1)

        # Parse date(s)
        dates_to_process = []

        if options.get("days_back"):
            days_back = options["days_back"]
            for i in range(days_back):
                dates_to_process.append((timezone.now() - timedelta(days=i + 1)).date())
        elif options.get("date"):
            try:
                report_date = date.fromisoformat(options["date"])
                dates_to_process.append(report_date)
            except ValueError:
                raise CommandError(f"Invalid date format: {options['date']}. Use YYYY-MM-DD.")
        else:
            # Default: yesterday
            dates_to_process.append((timezone.now() - timedelta(days=1)).date())

        # Get report class
        ReportClass = REPORT_REGISTRY[report_type]

        total_generated = 0
        errors = []

        for report_date in dates_to_process:
            self.stdout.write(self.style.HTTP_INFO(f"\n{'=' * 60}"))
            self.stdout.write(self.style.HTTP_INFO(f"Processing {report_type} report for {report_date}"))
            if academy_id:
                self.stdout.write(self.style.HTTP_INFO(f"Academy filter: {academy_id}"))
            self.stdout.write(self.style.HTTP_INFO(f"{'=' * 60}\n"))

            try:
                report = ReportClass(report_date=report_date, academy_id=academy_id)
                report.stdout = self  # Pass command for logging

                if dry_run:
                    raw_data = report.fetch_data()
                    reports = report.process_data(raw_data)
                    self.stdout.write(self.style.WARNING(f"DRY RUN: Would save {len(reports)} reports"))
                    total_generated += len(reports)
                else:
                    count = report.generate()
                    total_generated += count

            except Exception as e:
                error_msg = f"Error generating {report_type} for {report_date}: {e}"
                self.stdout.write(self.style.ERROR(error_msg))
                errors.append(error_msg)
                if verbosity > 1:
                    self.stdout.write(traceback.format_exc())
                continue

        # Summary
        self.stdout.write(self.style.HTTP_INFO(f"\n{'=' * 60}"))
        self.stdout.write(self.style.HTTP_INFO("SUMMARY"))
        self.stdout.write(self.style.HTTP_INFO(f"{'=' * 60}"))

        if dry_run:
            self.stdout.write(self.style.WARNING(f"DRY RUN - No data was saved"))

        self.stdout.write(self.style.SUCCESS(f"Total reports generated: {total_generated}"))
        self.stdout.write(f"Dates processed: {len(dates_to_process)}")

        if errors:
            self.stdout.write(self.style.ERROR(f"Errors encountered: {len(errors)}"))
            for error in errors:
                self.stdout.write(self.style.ERROR(f"  - {error}"))

        self.stdout.write("")

