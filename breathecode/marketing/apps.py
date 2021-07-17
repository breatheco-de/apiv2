from django.apps import AppConfig


class EventsConfig(AppConfig):
    name = 'breathecode.marketing'

    def ready(self):
        from . import receivers
