from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from breathecode.authenticate.models import ProfileAcademy


class Command(BaseCommand):
    help = "Fix ProfileAcademy records where users are missing their proper group assignments"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be fixed without making changes",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be made\n"))

        # Get the groups
        try:
            student_group = Group.objects.get(name="Student")
            teacher_group = Group.objects.get(name="Teacher")
            geek_creator_group = Group.objects.get(name="Geek Creator")
        except Group.DoesNotExist as e:
            self.stdout.write(self.style.ERROR(f"Error: Required group not found: {e}"))
            self.stdout.write(self.style.WARNING("Run 'python manage.py seed_groups' first"))
            return

        total_fixed = 0

        # Fix students
        self.stdout.write(self.style.MIGRATE_HEADING("\n=== Checking Students ==="))
        student_profiles = ProfileAcademy.objects.filter(
            role__slug="student", status="ACTIVE", user__isnull=False
        ).select_related("user", "role")

        fixed_students = 0
        for profile in student_profiles:
            if not profile.user.groups.filter(name="Student").exists():
                if not dry_run:
                    profile.user.groups.add(student_group)
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Fixed: {profile.user.email} (ID: {profile.user.id}) -> Student")
                )
                fixed_students += 1

        self.stdout.write(f"Students fixed: {fixed_students}")
        total_fixed += fixed_students

        # Fix teachers
        self.stdout.write(self.style.MIGRATE_HEADING("\n=== Checking Teachers ==="))
        teacher_profiles = ProfileAcademy.objects.filter(
            role__slug="teacher", status="ACTIVE", user__isnull=False
        ).select_related("user", "role")

        fixed_teachers = 0
        for profile in teacher_profiles:
            if not profile.user.groups.filter(name="Teacher").exists():
                if not dry_run:
                    profile.user.groups.add(teacher_group)
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Fixed: {profile.user.email} (ID: {profile.user.id}) -> Teacher")
                )
                fixed_teachers += 1

        self.stdout.write(f"Teachers fixed: {fixed_teachers}")
        total_fixed += fixed_teachers

        # Fix geek creators
        self.stdout.write(self.style.MIGRATE_HEADING("\n=== Checking Geek Creators ==="))
        gc_profiles = ProfileAcademy.objects.filter(
            role__slug="geek_creator", status="ACTIVE", user__isnull=False
        ).select_related("user", "role")

        fixed_gc = 0
        for profile in gc_profiles:
            if not profile.user.groups.filter(name="Geek Creator").exists():
                if not dry_run:
                    profile.user.groups.add(geek_creator_group)
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Fixed: {profile.user.email} (ID: {profile.user.id}) -> Geek Creator")
                )
                fixed_gc += 1

        self.stdout.write(f"Geek Creators fixed: {fixed_gc}")
        total_fixed += fixed_gc

        # Summary
        self.stdout.write(self.style.MIGRATE_HEADING("\n=== Summary ==="))
        if dry_run:
            self.stdout.write(self.style.WARNING(f"Would fix {total_fixed} users (DRY RUN)"))
        else:
            self.stdout.write(self.style.SUCCESS(f"✅ Total fixed: {total_fixed} users"))

        if total_fixed == 0:
            self.stdout.write(self.style.SUCCESS("✅ All groups are properly assigned!"))

