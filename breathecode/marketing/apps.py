from django.apps import AppConfig


class MarketingConfig(AppConfig):
    name = "breathecode.marketing"

    def ready(self):
        from . import receivers  # noqa: F401
