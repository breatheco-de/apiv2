import logging
from django.dispatch import receiver
from breathecode.monitoring.signals import github_webhook
from breathecode.monitoring.models import RepositoryWebhook
from .tasks import async_repository_issue_github

logger = logging.getLogger(__name__)


@receiver(github_webhook, sender=RepositoryWebhook)
def post_webhook_received(sender, instance, **kwargs):
    if instance.scope in ["issues", "issue_comment"]:
        logger.debug("Received github webhook signal for issues")
        async_repository_issue_github.delay(instance.id)
