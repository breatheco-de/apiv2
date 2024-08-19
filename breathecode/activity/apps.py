from django.apps import AppConfig


class ActivityConfig(AppConfig):
    name = "breathecode.activity"

    def ready(self):
        from . import flags  # noqa: F401
