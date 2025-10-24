"""
Management command to create UserInvite records for all staff users.

This ensures all Django staff members have proper UserInvite records with:
- is_email_validated = True
- status = ACCEPTED

Usage:
    python manage.py create_staff_invites
"""

import secrets
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from breathecode.authenticate.models import UserInvite


class Command(BaseCommand):
    help = "Create UserInvite records for all staff users with validated emails"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force update existing invites to ACCEPTED status",
        )

    def handle(self, *args, **options):
        force = options.get("force", False)
        verbosity = options.get("verbosity", 1)

        # Get all staff users
        staff_users = User.objects.filter(is_staff=True)

        if verbosity >= 1:
            self.stdout.write(f"\nFound {staff_users.count()} staff users")
            self.stdout.write("=" * 70)

        created = 0
        updated = 0
        skipped = 0

        for user in staff_users:
            # Check if UserInvite already exists for this user
            invite = UserInvite.objects.filter(email=user.email).first()

            if invite:
                # Update existing invite if force flag is set
                if force and (invite.status != "ACCEPTED" or not invite.is_email_validated):
                    invite.status = "ACCEPTED"
                    invite.is_email_validated = True
                    invite.process_status = "DONE"
                    invite.process_message = "Staff user - auto accepted"
                    if not invite.user:
                        invite.user = user
                    invite.save()
                    updated += 1

                    if verbosity >= 1:
                        self.stdout.write(self.style.SUCCESS(f"✓ Updated: {user.email} (set to ACCEPTED)"))
                else:
                    skipped += 1
                    if verbosity >= 2:
                        self.stdout.write(f"  Skipped: {user.email} (already exists)")
            else:
                # Create new UserInvite
                invite = UserInvite.objects.create(
                    email=user.email,
                    user=user,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    token=secrets.token_urlsafe(32),
                    is_email_validated=True,
                    status="ACCEPTED",
                    process_status="DONE",
                    process_message="Staff user - auto created",
                )
                created += 1

                if verbosity >= 1:
                    self.stdout.write(self.style.SUCCESS(f"✓ Created: {user.email}"))

        # Print summary
        if verbosity >= 1:
            self.stdout.write("\n" + "=" * 70)
            self.stdout.write(self.style.SUCCESS("Summary:"))
            self.stdout.write(f"  Created: {created}")
            self.stdout.write(f"  Updated: {updated}")
            self.stdout.write(f"  Skipped: {skipped}")
            self.stdout.write(f"  Total: {staff_users.count()}")

            if not force and updated == 0 and skipped > 0:
                self.stdout.write(
                    self.style.WARNING("\nTip: Use --force to update existing invites to ACCEPTED status")
                )
