import logging
from celery import shared_task, Task
from .models import Asset
from .actions import pull_from_github, test_asset

logger = logging.getLogger(__name__)


class BaseTaskWithRetry(Task):
    autoretry_for = (Exception, )
    #                                           seconds
    retry_kwargs = {'max_retries': 2, 'countdown': 60 * 10}
    retry_backoff = True


@shared_task
def async_pull_from_github(asset_slug, user_id=None):
    logger.debug(f'Synching asset {asset_slug} with data found on github')
    return pull_from_github(asset_slug)


@shared_task
def async_test_asset(asset_slug):
    a = Asset.objects.filter(slug=asset_slug).first()
    if a is None:
        logger.debug(f'Error: Error testing asset with slug {asset_slug}, does not exist.')

    try:
        if test_asset(a):
            return True
    except Exception as e:
        logger.exception(f'Error testing asset {a.slug}')

    return False
