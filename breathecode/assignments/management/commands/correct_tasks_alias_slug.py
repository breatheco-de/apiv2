from django.core.management.base import BaseCommand
from breathecode.registry.models import Asset
from breathecode.assignments.models import Task


class Command(BaseCommand):
    help = "Replace asset aliases with the current slugs"

    def handle(self, *args, **options):

        print("FIX TASKS")
        tasks = Task.objects.all()
        for task in tasks:
            associated_slug = task.associated_slug
            asset = Asset.get_by_slug(associated_slug)
            if asset is not None:
                if asset.lang not in ["us", "en"]:
                    english_translation = asset.all_translations.filter(lang__in=["en", "us"]).first()
                    english_slug = english_translation.slug
                    task.associated_slug = english_slug
                    task.save()

                # if the slug si different than the stored associated_slug it means that it is an alias
                elif asset.slug != associated_slug:
                    task.associated_slug = asset.slug
                    task.save()
