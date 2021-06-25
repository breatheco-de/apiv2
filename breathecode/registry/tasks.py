import logging
from celery import shared_task, Task
from .actions import sync_with_github

logger = logging.getLogger(__name__)


class BaseTaskWithRetry(Task):
    autoretry_for = (Exception, )
    #                                           seconds
    retry_kwargs = {'max_retries': 5, 'countdown': 60 * 5}
    retry_backoff = True


@shared_task
def async_sync_with_github(asset_slug, user_id=None):
    logger.debug("Synching asset {asset_slug} with data found on github")
    return sync_with_github(asset_slug)
