import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class RegistryConfig(AppConfig):
    name = "breathecode.provisioning"

    def ready(self):
        logger.debug("Loading provisioning.receivers")
        from . import receivers  # noqa: F401
