from django.apps import AppConfig


class FreelanceConfig(AppConfig):
    name = "breathecode.freelance"

    def ready(self):
        from . import receivers  # noqa: F401
