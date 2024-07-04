import logging

logger = logging.getLogger(__name__)


def test(self, webhook, payload: dict):
    logger.info("performing test request")
