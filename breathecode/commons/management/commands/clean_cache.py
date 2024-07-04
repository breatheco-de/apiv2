import time
import warnings
from django.core.management.base import BaseCommand

from django.core.cache import cache


class Command(BaseCommand):
    help = "Clean the cache"

    def handle(self, *args, **options):
        warnings.warn("Execute this command can degrade the performance of the application", stacklevel=3)

        self.stdout.write(self.style.WARNING("The cache will be cleaned in 3 seconds, press Ctrl+C to cancel"))

        time.sleep(3)

        cache.delete_pattern("*")
        self.stdout.write(self.style.SUCCESS("Cache cleaned"))
