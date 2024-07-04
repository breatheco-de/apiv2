from django.apps import AppConfig


class AcademyConfig(AppConfig):
    name = "breathecode.admissions"

    def ready(self):
        from . import receivers  # noqa: F401
