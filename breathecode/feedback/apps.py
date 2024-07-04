import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class FeedbackConfig(AppConfig):
    name = "breathecode.feedback"

    def ready(self):
        logger.debug("Loading feedback.receivers")
        from . import receivers  # noqa: F401
