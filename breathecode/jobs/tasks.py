import logging
from celery import shared_task, Task
from .models import Spider
from .actions import run_spider
from django.utils import timezone

logger = logging.getLogger(__name__)


class BaseTaskWithRetry(Task):
    autoretry_for = (Exception, )
    #                                           seconds
    retry_kwargs = {'max_retries': 5, 'countdown': 60 * 5}
    retry_backoff = True


@shared_task(bind=True, base=BaseTaskWithRetry)
def async_run_spider(self, args):
    logger.debug('Starting async_run_spider')
    now = timezone.now()
    _spider = Spider.objects.get(id=args['spi_id'])
    result = run_spider(_spider)

    if result.status_code == 200:
        logger.debug(f'Starting async_run_spider in spider name {_spider.name}')
        _spider.sync_status = 'SYNCHED'
        _spider.sync_desc = 'The run of the spider ended successfully command at ' + str(now)
        _spider.save()

    elif result.status_code == 400:
        message = '400 Bad Request command at ' + str(now)
        logger.debug(message)
        _spider.sync_status = 'ERROR'
        _spider.sync_desc = message + str(now)
        _spider.save()

    print('soy task ', result)
    return result
