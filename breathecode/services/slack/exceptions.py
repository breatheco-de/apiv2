import os
import logging

IS_TEST_ENV = os.getenv("ENV") == "test"
logger = logging.getLogger(__name__)


class SlackException(Exception):

    def __init__(self, message, slug=None):

        if IS_TEST_ENV and slug:
            logger.error(f"Slack error: {slug}")
            super().__init__(slug)
        else:
            logger.error(f"Slack error: {message}")
            super().__init__(message)
