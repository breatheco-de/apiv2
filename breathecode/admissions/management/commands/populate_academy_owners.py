"""
Management command to populate the owner field for academies.

This command finds the first admin (role='admin') from ProfileAcademy for each academy
and sets them as the owner.

Usage:
    python manage.py populate_academy_owners
"""

from django.core.management.base import BaseCommand
from breathecode.admissions.models import Academy
from breathecode.authenticate.models import ProfileAcademy, Role


class Command(BaseCommand):
    help = "Populate owner field for all academies from their first admin"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force update even if owner is already set",
        )

    def handle(self, *args, **options):
        force = options.get("force", False)
        verbosity = options.get("verbosity", 1)

        # Get the admin role
        admin_role = Role.objects.filter(slug="admin").first()
        if not admin_role:
            self.stdout.write(self.style.ERROR("✗ Admin role not found"))
            self.stdout.write("  Run: python manage.py create_academy_roles")
            return

        if verbosity >= 1:
            self.stdout.write("\nPopulating academy owners from ProfileAcademy")
            self.stdout.write("=" * 70)

        # Get all academies
        academies = Academy.objects.all()
        updated = 0
        skipped = 0
        no_admin = 0

        for academy in academies:
            # Skip if owner already set and not forcing
            if academy.owner and not force:
                skipped += 1
                if verbosity >= 2:
                    self.stdout.write(f"  Skipped: {academy.name} (already has owner: {academy.owner.email})")
                continue

            # Find the first admin for this academy
            first_admin = (
                ProfileAcademy.objects.filter(academy=academy, role=admin_role, status="ACTIVE")
                .order_by("created_at")
                .first()
            )

            if first_admin and first_admin.user:
                academy.owner = first_admin.user
                academy.save(update_fields=["owner"])
                updated += 1

                if verbosity >= 1:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✓ {academy.name} → {first_admin.user.email} "
                            f"({first_admin.user.first_name} {first_admin.user.last_name})"
                        )
                    )
            else:
                no_admin += 1
                if verbosity >= 1:
                    self.stdout.write(self.style.WARNING(f"⚠ {academy.name} → No active admin found"))

        # Print summary
        if verbosity >= 1:
            self.stdout.write("\n" + "=" * 70)
            self.stdout.write(self.style.SUCCESS("Summary:"))
            self.stdout.write(f"  Updated: {updated}")
            self.stdout.write(f"  Skipped (already set): {skipped}")
            self.stdout.write(f"  No admin found: {no_admin}")
            self.stdout.write(f"  Total academies: {academies.count()}")
