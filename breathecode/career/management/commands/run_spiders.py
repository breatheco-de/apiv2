from django.core.management.base import BaseCommand
from ...models import Spider
from ...tasks import async_run_spider
from django.utils import timezone


class Command(BaseCommand):
    help = "Synchronize from run_spider. Do not receive arguments."

    def handle(self, *args, **options):
        now = timezone.now()
        spiders = Spider.objects.all()
        count = 0
        for spi in spiders:
            if (
                spi.job is None
                or spi.job == ""
                or spi.zyte_project is None
                or spi.zyte_project == ""
                or spi.zyte_spider_number is None
                or spi.zyte_spider_number == ""
            ):
                spi.sync_status = "ERROR"
                spi.sync_desc = "Missing run_spider key or id"
                spi.save()
                self.stdout.write(self.style.ERROR(f"Spider {str(spi)} is missing run_spider key or ID"))
            else:
                spi.sync_status = "PENDING"
                spi.sync_desc = "Running run_spider command at " + str(now)
                spi.save()
                async_run_spider.delay({"spi_id": spi.id})
                count = count + 1

        self.stdout.write(self.style.SUCCESS(f"Enqueued {count} of {len(spiders)} for sync spider"))
