import logging, json
from celery import shared_task, Task
from django.db.models import F
from datetime import datetime
from .models import RepositoryIssueWebhook
from .actions import (sync_single_issue, update_status_based_on_github_action, generate_freelancer_bill)

logger = logging.getLogger(__name__)


class BaseTaskWithRetry(Task):
    autoretry_for = (Exception, )
    #                                           seconds
    retry_kwargs = {'max_retries': 5, 'countdown': 60 * 5}
    retry_backoff = True


@shared_task(bind=True, base=BaseTaskWithRetry)
def async_repository_issue_github(self, webhook_id):
    logger.debug('Starting async_repository_issue_github')
    status = 'ok'

    webhook = RepositoryIssueWebhook.objects.filter(id=webhook_id).first()
    if webhook is None:
        raise Exception(f'Github IssueWebhook with id {webhook_id} not found')
    webhook.status = 'PENDING'
    webhook.save()

    try:
        payload = json.loads(webhook.payload)

        comment = None
        if 'comment' in payload:
            comment = payload['comment']

        issue = sync_single_issue(issue=payload['issue'], comment=comment)
        issue.status = update_status_based_on_github_action(webhook.webhook_action, issue=issue)
        issue.save()

        if webhook.webhook_action in ['closed', 'reopened']:
            generate_freelancer_bill(issue.freelancer)

        webhook.status = 'DONE'
    except Exception as ex:
        webhook.status = 'ERROR'
        webhook.status_text = str(ex)
        logger.debug(ex)
        status = 'error'

    webhook.run_at = datetime.now()
    webhook.save()

    logger.debug(f'Github IssueWebook processing status: {status}')
