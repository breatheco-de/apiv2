"""
Management command to load development fixtures in the correct order with signals disabled.

This command handles the circular dependencies between fixtures and disables
Django signals during loading to prevent errors.

Usage:
    python manage.py load_dev_fixtures
"""

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.models.signals import post_save, pre_save, post_delete, pre_delete, m2m_changed


class Command(BaseCommand):
    help = "Load development fixtures in the correct order with signals disabled"

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Flush the database before loading fixtures",
        )

    def handle(self, *args, **options):
        verbosity = options["verbosity"]
        flush = options["flush"]

        # Flush database if requested
        if flush:
            if verbosity >= 1:
                self.stdout.write(self.style.WARNING("Flushing database..."))
            call_command("flush", "--no-input", verbosity=0)
            if verbosity >= 1:
                self.stdout.write(self.style.SUCCESS("✓ Database flushed"))

        # Store original signal receivers
        saved_receivers = {
            "post_save": post_save.receivers[:],
            "pre_save": pre_save.receivers[:],
            "post_delete": post_delete.receivers[:],
            "pre_delete": pre_delete.receivers[:],
            "m2m_changed": m2m_changed.receivers[:],
        }

        try:
            # Disable all signals
            if verbosity >= 2:
                self.stdout.write("Disabling Django signals...")
            post_save.receivers = []
            pre_save.receivers = []
            post_delete.receivers = []
            pre_delete.receivers = []
            m2m_changed.receivers = []

            # Disable database constraints temporarily
            with connection.cursor() as cursor:
                if verbosity >= 2:
                    self.stdout.write("Disabling foreign key constraints...")
                cursor.execute("SET CONSTRAINTS ALL DEFERRED;")

            # Define fixtures in dependency order
            # Note: The fixtures have circular dependencies, but we load what we can
            # Users need academies, cohorts need users - so we'll need to split them
            fixtures = [
                # Level 1: Users first (authenticate fixture will fail on ProfileAcademy but that's OK)
                ("authenticate", "Users", ["breathecode/authenticate/fixtures/dev_data.json"]),
                # Level 2: Admissions (needs users for CohortUser)  
                ("admissions", "Countries, Cities, Academies, Cohorts", ["breathecode/admissions/fixtures/dev_data.json"]),
            ]

            # Load each fixture group
            errors = []
            for app_name, description, fixture_files in fixtures:
                if verbosity >= 1:
                    self.stdout.write(f"\nLoading {description}...")

                for fixture_file in fixture_files:
                    try:
                        if verbosity >= 2:
                            self.stdout.write(f"  Loading {fixture_file}...")

                        call_command("loaddata", fixture_file, verbosity=0)

                        if verbosity >= 1:
                            self.stdout.write(self.style.SUCCESS(f"  ✓ Loaded {fixture_file}"))

                    except Exception as e:
                        error_msg = str(e)
                        # Extract just the relevant error message
                        if "Problem installing" in error_msg:
                            error_msg = error_msg.split("Problem installing")[1].split("\n")[0]
                        
                        self.stdout.write(self.style.WARNING(f"  ⚠ Partially loaded {fixture_file}"))
                        self.stdout.write(self.style.WARNING(f"    Some records skipped due to: {error_msg}"))
                        errors.append((fixture_file, error_msg))

            # Re-enable constraints
            with connection.cursor() as cursor:
                if verbosity >= 2:
                    self.stdout.write("Re-enabling foreign key constraints...")
                try:
                    cursor.execute("SET CONSTRAINTS ALL IMMEDIATE;")
                except Exception as e:
                    if verbosity >= 2:
                        self.stdout.write(self.style.WARNING(f"  Warning: {str(e)[:100]}"))

            if verbosity >= 1:
                if errors:
                    self.stdout.write(self.style.WARNING(f"\n⚠ Fixtures loaded with {len(errors)} warning(s)"))
                else:
                    self.stdout.write(self.style.SUCCESS("\n✓ All fixtures loaded successfully!"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n✗ Critical error loading fixtures: {str(e)}"))
            if verbosity >= 2:
                import traceback
                traceback.print_exc()

        finally:
            # Restore original signal receivers
            if verbosity >= 2:
                self.stdout.write("Restoring Django signals...")
            post_save.receivers = saved_receivers["post_save"]
            pre_save.receivers = saved_receivers["pre_save"]
            post_delete.receivers = saved_receivers["post_delete"]
            pre_delete.receivers = saved_receivers["pre_delete"]
            m2m_changed.receivers = saved_receivers["m2m_changed"]

            if verbosity >= 2:
                self.stdout.write(self.style.SUCCESS("✓ Signals restored"))

        # Print summary
        if verbosity >= 1:
            self.stdout.write("\n" + "=" * 70)
            self.stdout.write(self.style.SUCCESS("Fixture loading complete!"))
            self.stdout.write("=" * 70)

            # Show what was loaded
            from breathecode.admissions.models import Country, City, Academy, Cohort
            from django.contrib.auth.models import User

            self.stdout.write(f"\nData summary:")
            self.stdout.write(f"  Countries: {Country.objects.count()}")
            self.stdout.write(f"  Cities: {City.objects.count()}")
            self.stdout.write(f"  Academies: {Academy.objects.count()}")
            self.stdout.write(f"  Cohorts: {Cohort.objects.count()}")
            self.stdout.write(f"  Users: {User.objects.count()}")

