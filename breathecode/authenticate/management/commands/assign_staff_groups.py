"""
Management command to assign Django groups to staff users.

By default, assigns the 'Admin' group to all superusers/staff users.

Usage:
    python manage.py assign_staff_groups
    python manage.py assign_staff_groups --group="Creator"
    python manage.py assign_staff_groups --superusers-only
"""

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Assign Django groups to staff users"

    def add_arguments(self, parser):
        parser.add_argument(
            "--group",
            type=str,
            default="Admin",
            help="Name of the group to assign (default: Admin)",
        )
        parser.add_argument(
            "--superusers-only",
            action="store_true",
            help="Only assign to superusers, not all staff",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force add even if user already has the group",
        )

    def handle(self, *args, **options):
        group_name = options["group"]
        superusers_only = options.get("superusers_only", False)
        verbosity = options.get("verbosity", 1)

        # Get the group
        try:
            group = Group.objects.get(name=group_name)
        except Group.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"✗ Group '{group_name}' does not exist"))
            self.stdout.write("\nAvailable groups:")
            for g in Group.objects.all().order_by("name"):
                self.stdout.write(f"  - {g.name}")
            return

        # Get users to assign
        if superusers_only:
            users = User.objects.filter(is_superuser=True)
            user_type = "superusers"
        else:
            users = User.objects.filter(is_staff=True)
            user_type = "staff users"

        if verbosity >= 1:
            self.stdout.write(f"\nAssigning '{group_name}' group to {users.count()} {user_type}")
            self.stdout.write("=" * 70)

        added = 0
        skipped = 0

        for user in users:
            if user.groups.filter(name=group_name).exists():
                skipped += 1
                if verbosity >= 2:
                    self.stdout.write(f"  Skipped: {user.email} (already has group)")
            else:
                user.groups.add(group)
                added += 1
                if verbosity >= 1:
                    self.stdout.write(self.style.SUCCESS(f"✓ Added: {user.email}"))

        # Print summary
        if verbosity >= 1:
            self.stdout.write("\n" + "=" * 70)
            self.stdout.write(self.style.SUCCESS("Summary:"))
            self.stdout.write(f"  Added to group: {added}")
            self.stdout.write(f"  Already had group: {skipped}")
            self.stdout.write(f"  Total users: {users.count()}")

            # Show user's groups
            if verbosity >= 2 and users.count() > 0:
                first_user = users.first()
                self.stdout.write(f"\nExample: {first_user.email} now has groups:")
                for g in first_user.groups.all():
                    self.stdout.write(f"  - {g.name}")
