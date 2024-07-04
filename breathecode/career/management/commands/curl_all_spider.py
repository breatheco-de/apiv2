from django.core.management.base import BaseCommand
from ...models import Spider
from ...tasks import async_fetch_sync_all_data
from django.utils import timezone


class Command(BaseCommand):
    help = "Synchronize from run_spider. Do not receive arguments."

    def handle(self, *args, **options):
        now = timezone.now()
        spiders = Spider.objects.all()
        count = 0
        for spi in spiders:
            if (
                spi.zyte_project.zyte_api_deploy is None
                or spi.zyte_project.zyte_api_deploy == ""
                or spi.zyte_spider_number is None
                or spi.zyte_spider_number == ""
                or spi.zyte_job_number is None
                or spi.zyte_job_number == ""
                or spi.zyte_project.zyte_api_key is None
                or spi.zyte_project.zyte_api_key == ""
            ):
                spi.sync_status = "ERROR"
                spi.sync_desc = "Missing the spider's args (Invalid args)"
                spi.save()
                self.stdout.write(self.style.ERROR(f"Spider {str(spi)} is missing async_fetch_sync_all_data key or ID"))
            else:
                spi.sync_status = "PENDING"
                spi.sync_desc = "Running run_spider command at " + str(now)
                spi.save()
                async_fetch_sync_all_data.delay({"spi_id": spi.id})
                count = count + 1

        self.stdout.write(self.style.SUCCESS(f"Enqueued {count} of {len(spiders)} for async fetch all spiders"))
