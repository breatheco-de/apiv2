from django.core.management.commands.migrate import Command as MigrateCommand
from django.db.models.signals import post_migrate
from django.apps import apps

class Command(MigrateCommand):
    def handle(self, *args, **options):
        # Disconnect post_migrate signals for contenttypes and auth
        for app_config in apps.get_app_configs():
            if app_config.label in ('contenttypes', 'auth'):
                post_migrate.receivers = [
                    r for r in post_migrate.receivers
                    if r.__self__.__module__ != f'{app_config.name}.management'
                ]
        # Run the migration
        super().handle(*args, **options)
