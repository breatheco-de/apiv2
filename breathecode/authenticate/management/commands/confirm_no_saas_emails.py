from django.db.models import Q
from django.core.management.base import BaseCommand
from ...models import UserInvite


class Command(BaseCommand):
    help = "Confirm all the emails that are not from a saas academy"

    def handle(self, *args, **options):
        invites = UserInvite.objects.filter(
            Q(academy__available_as_saas=False) | Q(cohort__academy__available_as_saas=False), is_email_validated=False
        )

        n = invites.count()
        invites.update(is_email_validated=True)

        self.stdout.write(self.style.SUCCESS(f"Successfully confirmed {n} invites"))
