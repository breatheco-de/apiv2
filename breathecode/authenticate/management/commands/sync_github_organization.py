from django.core.management.base import BaseCommand
from ...actions import sync_organization_members
from ...models import AcademyAuthSettings


class Command(BaseCommand):
    help = "Delete expired temporal and login tokens"

    def handle(self, *args, **options):

        aca_settings = AcademyAuthSettings.objects.filter(github_is_sync=True)
        for settings in aca_settings:
            print(f"Synching academy {settings.academy.name} organization users")
            try:
                sync_organization_members(settings.academy.id)
            except Exception as e:
                print(f"Error synching members for academy {settings.academy.id}: " + str(e))
