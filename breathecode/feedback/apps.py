import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class FeedbackConfig(AppConfig):
    name = "breathecode.feedback"

    def ready(self):
        from . import receivers  # noqa: F401
        from . import supervisors  # noqa: F401
