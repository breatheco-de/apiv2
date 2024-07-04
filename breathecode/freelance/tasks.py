import logging

from celery import shared_task

from breathecode.monitoring.decorators import WebhookTask
from breathecode.utils import TaskPriority

from .actions import generate_freelancer_bill, sync_single_issue, update_status_based_on_github_action

logger = logging.getLogger(__name__)


@shared_task(bind=True, base=WebhookTask, priority=TaskPriority.BILL.value)
def async_repository_issue_github(self, webhook):

    logger.debug("async_repository_issue_github")
    payload = webhook.get_payload()

    comment = None
    if "comment" in payload:
        comment = payload["comment"]

    issue = sync_single_issue(issue=payload["issue"], comment=comment, academy_slug=webhook.academy_slug)
    issue.status = update_status_based_on_github_action(webhook.webhook_action, issue=issue)
    issue.save()

    if webhook.webhook_action in ["closed", "reopened"]:
        generate_freelancer_bill(issue.freelancer)

    return webhook
