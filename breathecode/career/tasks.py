import logging

from celery import shared_task
from django.utils import timezone

from breathecode.utils import TaskPriority

from .models import Spider

logger = logging.getLogger(__name__)


@shared_task(bind=True, priority=TaskPriority.BACKGROUND.value)
def async_run_spider(self, args):
    from .actions import run_spider

    logger.error("Starting async_run_spider")
    now = timezone.now()
    spider = Spider.objects.filter(id=args["spi_id"]).first()
    result = run_spider(spider)

    if result:
        logger.error(f"Starting async_run_spider in spider name {spider.name}")
        spider.spider_last_run_status = "SYNCHED"
        spider.spider_last_run_desc = "The run of the spider ended successfully command at " + str(now)
        spider.save()


@shared_task(bind=True, priority=TaskPriority.BACKGROUND.value)
def async_fetch_sync_all_data(self, args):
    from .actions import fetch_sync_all_data

    logger.error("Starting async_fetch_sync_all_data")
    now = timezone.now()
    spider = Spider.objects.filter(id=args["spi_id"]).first()
    result = fetch_sync_all_data(spider)

    if result:
        message = f"Starting async_fetch_sync_all_data in spider name {spider.name}"
        logger.error(message)
        spider.sync_status = "SYNCHED"
        spider.sync_desc = message + str(now)
        spider.save()
