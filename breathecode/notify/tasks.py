import logging
from celery import shared_task, Task
from .models import SlackTeam
from .actions import sync_slack_team_channel, sync_slack_team_users
from breathecode.services.slack.client import Slack

logger = logging.getLogger(__name__)


class BaseTaskWithRetry(Task):
    autoretry_for = (Exception, )
    #                                           seconds
    retry_kwargs = {'max_retries': 5, 'countdown': 60 * 5}
    retry_backoff = True


@shared_task
def async_slack_team_channel(team_id):
    logger.debug("Starting async_slack_team_channel")
    return sync_slack_team_channel(team_id)


@shared_task
def async_slack_team_users(team_id):
    logger.debug("Starting async_slack_team_users")
    return sync_slack_team_users(team_id)


@shared_task
def async_slack_action(post_data):
    logger.debug("Starting async_slack_action")
    try:
        client = Slack()
        success = client.execute_action(context=post_data)
        if success:
            logger.debug("Successfully process slack action")
            return True
        else:
            logger.error("Error processing slack action")
            return False

    except Exception as e:
        logger.exception("Error processing slack action")
        return False
