import json
from django.core.management.base import BaseCommand
from .models import SyllabusVersion
from breathecode.registry.models import Asset


class Command(BaseCommand):
    help = "Replace asset aliases in the syllabus with the current slugs"

    def handle(self, *args, **options):
        try:
            from breathecode.certificate.actions import syllabus_weeks_to_days

            syllabus_list = SyllabusVersion.objects.all()
            key_map = {
                "QUIZ": "quizzes",
                "LESSON": "lessons",
                "EXERCISE": "replits",
                "PROJECT": "assignments",
            }

            for s in syllabus_list:
                if isinstance(s.json, str):
                    s.json = json.loads(s.json)

                # in case the json contains "weeks" instead of "days"
                s.json = syllabus_weeks_to_days(s.json)

                for module_index, day in enumerate(s.json["days"]):

                    for asset_type in key_map:
                        if key_map[asset_type] not in day:
                            continue

                        for asset_index, assignment in enumerate(day[key_map[asset_type]]):
                            assignment_slug = assignment["slug"] if isinstance(assignment, dict) else assignment
                            asset = Asset.get_by_slug(assignment_slug)

                            if asset is not None and (asset.lang not in ["us", "en"] or asset.slug != assignment_slug):
                                updated_slug = assignment_slug

                                if asset.lang not in ["us", "en"]:
                                    english_translation = asset.all_translations.filter(lang__in=["en", "us"]).first()
                                    updated_slug = english_translation.slug
                                elif asset.slug != assignment_slug:
                                    updated_slug = asset.slug

                                if isinstance(assignment, dict):
                                    s.json["days"][module_index][key_map[asset_type]][asset_index][
                                        "slug"
                                    ] = updated_slug
                                else:
                                    s.json["days"][module_index][key_map[asset_type]][asset_index] = updated_slug

                                s.save()

        except Exception:
            self.stderr.write("Failed to fix assets slugs in all syllabus")
