from django.core.management.base import BaseCommand
from linked_services.django.models import App, AppOptionalScope, AppRequiredScope, Scope

# if it does not require an agreement, add scopes is not necessary
APPS = [
    {
        "name": "Rigobot",
        "slug": "rigobot",
        "require_an_agreement": False,
        "required_scopes": [],
        "optional_scopes": [],
    },
]

SCOPES = [
    {
        "name": "Read user",
        "slug": "read:user",
        "description": "Can read user information",
    },
    {
        "name": "Webhook",
        "slug": "webhook",
        "description": "Can receive updates from 4Geeks",
    },
]


class Command(BaseCommand):
    help = "Create default system capabilities"

    def handle(self, *args, **options):
        cache = {}
        for scope in SCOPES:
            slug = scope["slug"]
            x, created = Scope.objects.get_or_create(slug=slug, defaults=scope)

            if not created:
                for key, value in scope.items():
                    setattr(x, key, value)
                x.save()

            cache[slug] = x

        for app in APPS:
            slug = app["slug"]
            required_scopes = app["required_scopes"]
            optional_scopes = app["optional_scopes"]

            x = App.objects.filter(slug=slug).first()
            if not x:
                continue

            for key, value in app.items():
                if key == "required_scopes" or key == "optional_scopes":
                    continue

                setattr(x, key, value)

            x.save()

            for k in required_scopes:
                AppRequiredScope.objects.get_or_create(app=x, scope=cache[k])

            for k in optional_scopes:
                AppOptionalScope.objects.get_or_create(app=x, scope=cache[k])
