from django.core.management.commands.migrate import Command as MigrateCommand
from django.db.models.signals import post_migrate
from django.apps import apps

class Command(MigrateCommand):
    def handle(self, *args, **options):
        # Disconnect post_migrate signals for contenttypes and auth
        for app_config in apps.get_app_configs():
            if app_config.label in ('contenttypes', 'auth'):
                # Filter out receivers from contenttypes and auth management modules
                post_migrate.receivers = [
                    r for r in post_migrate.receivers
                    if not (
                        hasattr(r, 'receiver') and  # Check if receiver attribute exists
                        r.receiver.__module__.startswith(f'{app_config.name}.management')
                    )
                ]
        # Run the migration
        super().handle(*args, **options)
