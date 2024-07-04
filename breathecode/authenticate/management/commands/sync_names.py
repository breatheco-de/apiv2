from django.db.models import Q
from django.core.management.base import BaseCommand
from ...models import ProfileAcademy


class Command(BaseCommand):
    help = "Delete expired temporal and login tokens"

    def handle(self, *args, **options):

        empty_profiles = ProfileAcademy.objects.filter(
            Q(first_name__isnull=True) | Q(first_name=""), Q(user__first_name__isnull=False)
        )
        print(f"Found {str(empty_profiles.count())} profiles out of sync")

        save = False
        for profile in empty_profiles:
            if profile.user is None:
                continue

            if profile.first_name is None or profile.first_name == "":
                if profile.user.first_name is not None and profile.user.first_name != "":
                    save = True
                    profile.first_name = profile.user.first_name

            if profile.last_name is None or profile.last_name == "":
                if profile.user.last_name is not None and profile.user.last_name != "":
                    save = True
                    profile.last_name = profile.user.last_name

            if save:
                profile.save()

        profiles = ProfileAcademy.objects.filter(
            Q(first_name__isnull=False), Q(user__first_name__isnull=True) | Q(user__first_name="")
        )
        print(f"Found {str(profiles.count())} users out of sync")
        for p in profiles:
            if p.user is None:
                continue

            if p.user.first_name is None or p.user.first_name == "":
                if p.first_name is not None and p.first_name != "":
                    save = True
                    p.user.first_name = p.first_name

            if p.user.last_name is None or p.user.last_name == "":
                if p.last_name is not None and p.last_name != "":
                    save = True
                    p.user.last_name = p.last_name

            if save:
                p.user.save()
