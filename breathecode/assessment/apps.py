from django.apps import AppConfig  # noqa: F401


class AssessmentConfig(AppConfig):
    name = "breathecode.assessment"

    def ready(self):
        from . import receivers  # noqa: F401
