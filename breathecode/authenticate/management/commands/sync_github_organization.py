import os, requests, sys, pytz
from datetime import datetime
from django.db.models import Q
from django.core.management.base import BaseCommand, CommandError
from ...actions import sync_organization_members
from ...models import AcademyAuthSettings


class Command(BaseCommand):
    help = 'Delete expired temporal and login tokens'

    def handle(self, *args, **options):

        aca_settings = AcademyAuthSettings.objects.filter(github_is_sync=True)
        for settings in aca_settings:
            print(f'Synching academy {settings.academy.name} organization users')
            sync_organization_members(settings.academy.id)
