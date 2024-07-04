from django.apps import AppConfig


class NotifyConfig(AppConfig):
    name = "breathecode.notify"

    def ready(self):
        from . import receivers  # noqa: F401
