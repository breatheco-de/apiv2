import os, requests, sys, pytz
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError

from ...actions import delete_tokens


class Command(BaseCommand):
    help = 'Delete expired temporal and login tokens'

    def handle(self, *args, **options):
        count = delete_tokens()
        print(f"{count} tokens were deleted")
