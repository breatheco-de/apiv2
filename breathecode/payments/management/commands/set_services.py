from django.core.management.base import BaseCommand

from breathecode.payments.models import Service, ServiceTranslation

GROUP = {"codename": "CLASSROOM"}

SERVICES = [
    {
        "slug": "backend-with-django",
        "private": False,
        "price_per_unit": 4000,
        "currency": "USD",
        "groups": ["CLASSROOM"],
        # 'cohorts': '^miami-backend-\w+$',
        "translations": {
            "en": {
                "title": "Backend with DJango",
                "description": "...",
            },
            "es": {
                "title": "Backend con DJango",
                "description": "...",
            },
        },
    },
    {
        "slug": "frontend-with-react",
        "private": False,
        "price_per_unit": 4000,
        "currency": "USD",
        "groups": ["CLASSROOM"],
        "translations": {
            "en": {
                "title": "Backend with DJango",
                "description": "...",
            },
            "es": {
                "title": "Backend con DJango",
                "description": "...",
            },
        },
    },
]


class Command(BaseCommand):
    help = "Set currencies"

    def handle(self, *args, **options):
        # groups
        for service in SERVICES:
            s, _ = Service.objects.get_or_create(
                slug=service["slug"],
                defaults={
                    "price_per_unit": service["price_per_unit"],
                    "owner": None,
                    "private": False,
                    "groups": [],
                },
            )

            for lang in service["translations"]:
                ServiceTranslation.objects.get_or_create(
                    service=s,
                    lang=lang,
                    defaults={
                        "title": service["translations"][lang]["title"],
                        "description": service["translations"][lang]["description"],
                    },
                )
