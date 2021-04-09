import os, requests, sys, pytz
from django.core.management.base import BaseCommand, CommandError
from ...models import Asset

HOST_ASSETS = "https://assets.breatheco.de/apis"
API_URL = os.getenv("API_URL","")
HOST_ASSETS = "https://assets.breatheco.de/apis"
HOST = os.environ.get("OLD_BREATHECODE_API")
DATETIME_FORMAT="%Y-%m-%d"

class Command(BaseCommand):
    help = 'Sync academies from old breathecode'

    def handle(self, *args, **options):

        response = requests.get(f"{HOST_ASSETS}/registry/all")
        items = response.json()

        for slug in items:
            data = items[slug]
            a = Asset.objects.filter(slug=slug).first()
            if a is None:
                a = Asset(
                    slug=slug,
                    asset_type="EXERCISE"
                )
                self.stdout.write(self.style.SUCCESS(f"Adding asset {a.slug}"))
            else:
                self.stdout.write(self.style.SUCCESS(f"Updating asset {slug}"))

            a.title = data['title']
            a.lang = data['language']
            a.url = data['repository']
            a.readme = data['readme']
            
            if "intro" in data:
                a.intro_video_url = data['intro']
            if "description" in data:
                a.description = data['description']
            if "duration" in data:
                a.duration = data['duration']
            if "difficulty" in data:
                a.difficulty = data['difficulty']
            if "graded" in data:
                a.graded = data['graded']
            if "preview" in data:
                a.preview = data['preview']
            if "video-solutions" in data:
                a.with_solutions = data['video-solutions']

            a.save()
