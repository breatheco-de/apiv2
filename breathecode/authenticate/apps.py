from django.apps import AppConfig


class AcademyConfig(AppConfig):
    name = "breathecode.authenticate"

    def ready(self):
        from . import receivers  # noqa: F401
        from . import flags  # noqa: F401
