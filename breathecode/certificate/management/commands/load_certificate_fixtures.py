from django.core.management.base import BaseCommand
from django.core.management import call_command
import os


class Command(BaseCommand):
    help = "Load certificate fixtures for Full Stack Developer and Data Scientist"

    def add_arguments(self, parser):
        # BaseCommand already provides --verbosity argument
        pass

    def handle(self, *args, **options):
        verbosity = options.get("verbosity", 1)
        
        # Get the directory of this command
        command_dir = os.path.dirname(os.path.abspath(__file__))
        certificate_dir = os.path.dirname(os.path.dirname(command_dir))
        certificate_fixtures_dir = os.path.join(certificate_dir, "fixtures")
        
        # Get admissions fixtures directory
        admissions_dir = os.path.dirname(certificate_dir)
        admissions_fixtures_dir = os.path.join(admissions_dir, "admissions", "fixtures")
        
        # List of fixture files to load in order with their directories
        fixture_files = [
            (admissions_fixtures_dir, "data_science_syllabus.json"),  # Load syllabus first
            (certificate_fixtures_dir, "certificate_specialties.json"),  # Then specialties and badges
        ]
        
        self.stdout.write(
            self.style.SUCCESS("Loading certificate fixtures...")
        )
        
        for fixtures_dir, fixture_file in fixture_files:
            fixture_path = os.path.join(fixtures_dir, fixture_file)
            
            if not os.path.exists(fixture_path):
                self.stdout.write(
                    self.style.WARNING(f"Fixture file not found: {fixture_path}")
                )
                continue
                
            try:
                self.stdout.write(f"Loading {fixture_file}...")
                call_command(
                    "loaddata",
                    fixture_path,
                    verbosity=verbosity - 1,  # Reduce verbosity for loaddata
                )
                self.stdout.write(
                    self.style.SUCCESS(f"Successfully loaded {fixture_file}")
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Error loading {fixture_file}: {str(e)}")
                )
                if verbosity >= 2:
                    import traceback
                    self.stdout.write(traceback.format_exc())
        
        self.stdout.write(
            self.style.SUCCESS("Certificate fixtures loading completed!")
        )
