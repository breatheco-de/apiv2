import logging

from breathecode.assignments.models import LearnPackWebhook

logger = logging.getLogger(__name__)


def test(self, webhook: LearnPackWebhook):
    logger.info("performing test request")
