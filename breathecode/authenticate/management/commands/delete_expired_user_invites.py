from django.core.management.base import BaseCommand
from django.utils import timezone

from breathecode.authenticate.models import ProfileAcademy, UserInvite


class Command(BaseCommand):
    help = "Delete expired user invites that are pending and their associated users if they meet certain conditions"

    def handle(self, *args, **options):
        now = timezone.now()

        # Get all expired and pending user invites
        expired_invites = UserInvite.objects.filter(status="PENDING", expires_at__lt=now, expires_at__isnull=False)
        deleted_invites = 0
        deleted_users = 0

        for invite in expired_invites:
            user = invite.user

            if user:
                # Check if user has other non-expired or accepted invites
                other_invites = (
                    UserInvite.objects.filter(user=user)
                    .exclude(id=invite.id)
                    .filter(status__in=["PENDING", "ACCEPTED"])
                )

                # Check if user has a profile academy
                has_profile_academy = ProfileAcademy.objects.filter(user=user).exists()

                # Only delete if user has no other invites and no profile academy
                if not other_invites.exists() and not has_profile_academy:
                    user.delete()
                    deleted_users += 1

            invite.delete()
            deleted_invites += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully deleted {deleted_invites} expired invites and {deleted_users} associated users"
            )
        )
