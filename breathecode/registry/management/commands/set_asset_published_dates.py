import os, requests, logging
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.utils import timezone
from ...models import Asset
from breathecode.admissions.models import Academy
from ...tasks import async_pull_from_github
from slugify import slugify
import re

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Set published date to legacy articles'

    def handle(self, *args, **options):

        assets = Asset.objects.filter(published_at__isnull=True, status='PUBLISHED',category__isnull=False)
        for a in assets:
            a.published_at = a.updated_at
            a.save()
