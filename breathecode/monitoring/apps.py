import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class MonitoringConfig(AppConfig):
    name = "breathecode.monitoring"

    def ready(self):
        logger.debug("Loading monitoring.receivers")
        from . import receivers  # noqa: F401
