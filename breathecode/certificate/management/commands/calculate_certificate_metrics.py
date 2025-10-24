import logging
from django.core.management.base import BaseCommand
from django.utils import timezone

from breathecode.certificate.models import Specialty, UserSpecialty

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Calculate and update certificate metrics for all specialties"

    def add_arguments(self, parser):
        parser.add_argument(
            "--specialty-slug",
            type=str,
            help="Calculate metrics for a specific specialty slug only",
        )
        parser.add_argument(
            "--status",
            type=str,
            choices=["ACTIVE", "INACTIVE", "DELETED"],
            help="Calculate metrics only for specialties with this status",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be updated without making changes",
        )

    def handle(self, *args, **options):
        specialty_slug = options.get("specialty_slug")
        status_filter = options.get("status")
        dry_run = options.get("dry_run", False)

        if specialty_slug:
            specialties = Specialty.objects.filter(slug=specialty_slug)
            if not specialties.exists():
                self.stdout.write(self.style.ERROR(f"Specialty with slug '{specialty_slug}' not found"))
                return
        else:
            specialties = Specialty.objects.all()

        # Apply status filter if provided
        if status_filter:
            specialties = specialties.filter(status=status_filter)

        self.stdout.write(self.style.SUCCESS(f"Calculating metrics for {specialties.count()} specialties..."))

        updated_count = 0
        for specialty in specialties:
            metrics = self.calculate_specialty_metrics(specialty)

            if dry_run:
                self.stdout.write(f"[DRY RUN] Would update {specialty.slug}: {metrics}")
            else:
                specialty.metrics = metrics
                specialty.save(update_fields=["metrics"])
                self.stdout.write(self.style.SUCCESS(f"Updated {specialty.slug}: {metrics}"))
                updated_count += 1

        if dry_run:
            self.stdout.write(self.style.WARNING(f"[DRY RUN] Would have updated {specialties.count()} specialties"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Successfully updated {updated_count} specialties"))

    def calculate_specialty_metrics(self, specialty):
        """
        Calculate metrics for a specific specialty.

        Args:
            specialty: Specialty instance

        Returns:
            dict: Metrics data
        """
        # Get all issued certificates for this specialty
        issued_certificates = UserSpecialty.objects.filter(specialty=specialty, status="PERSISTED").select_related(
            "academy"
        )

        # Count total issued certificates
        total_issued = issued_certificates.count()

        # Calculate breakdown by academy
        academy_breakdown = {}
        for cert in issued_certificates:
            academy_slug = cert.academy.slug
            academy_breakdown[academy_slug] = academy_breakdown.get(academy_slug, 0) + 1

        # Get current timestamp
        now = timezone.now()

        return {
            "total_issued": total_issued,
            "total_issued_by_academy": academy_breakdown,
            "last_updated": now.isoformat(),
            "version": "1.0",
        }
