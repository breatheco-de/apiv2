import logging
from celery import shared_task, Task
from django.db.models import F
from datetime import datetime
from breathecode.monitoring.decorators import github_webhook_task
from .actions import (sync_single_issue, update_status_based_on_github_action, generate_freelancer_bill)

logger = logging.getLogger(__name__)


class BaseTaskWithRetry(Task):
    autoretry_for = (Exception, )
    #                                           seconds
    retry_kwargs = {'max_retries': 5, 'countdown': 60 * 5}
    retry_backoff = True


@shared_task(bind=True, base=BaseTaskWithRetry)
@github_webhook_task()
def async_repository_issue_github(self, webhook):

    payload = webhook.get_payload()

    comment = None
    if 'comment' in payload:
        comment = payload['comment']

    issue = sync_single_issue(issue=payload['issue'], comment=comment, academy_slug=webhook.academy_slug)
    issue.status = update_status_based_on_github_action(webhook.webhook_action, issue=issue)
    issue.save()

    if webhook.webhook_action in ['closed', 'reopened']:
        generate_freelancer_bill(issue.freelancer)

    return webhook
