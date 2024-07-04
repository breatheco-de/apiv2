import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class RegistryConfig(AppConfig):
    name = "breathecode.registry"

    def ready(self):
        logger.debug("Loading registry.receivers")
        from . import receivers  # noqa: F401
