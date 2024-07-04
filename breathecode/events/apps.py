from django.apps import AppConfig


class EventsConfig(AppConfig):
    name = "breathecode.events"

    def ready(self):
        from . import receivers  # noqa
