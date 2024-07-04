from django.apps import AppConfig


class MediaConfig(AppConfig):
    name = "breathecode.mentorship"

    def ready(self):
        from . import receivers  # noqa: F401
