from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group


class Command(BaseCommand):
    help = "Add Legacy group to all current users"

    def handle(self, *args, **options):
        try:
            legacy_group = Group.objects.filter(name="Legacy").first()
            for user in User.objects.all():
                if legacy_group not in user.groups.all():
                    user.groups.add(legacy_group)
        except Exception:
            self.stderr.write("Failed to add the Legacy group to all users")
