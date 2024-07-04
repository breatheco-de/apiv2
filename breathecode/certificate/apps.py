from django.apps import AppConfig


class CertificateConfig(AppConfig):
    name = "breathecode.certificate"

    def ready(self):
        from . import receivers  # noqa
