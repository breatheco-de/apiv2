from django.utils import timezone
from datetime import timedelta
from unittest.mock import MagicMock, call, patch
from ..mixins import CareerTestCase
from breathecode.tests.mocks import (
    REQUESTS_PATH,
    apply_requests_post_mock,
)

from ...tasks import async_fetch_sync_all_data

spider = {"name": "getonboard", "zyte_spider_number": 4, "zyte_job_number": 0}
zyte_project = {"zyte_api_key": 1234567, "zyte_api_deploy": 223344}
platform = {"name": "getonboard"}


class AsyncFetchSyncAllDataTaskTestCase(CareerTestCase):

    @patch("breathecode.career.actions.fetch_sync_all_data", MagicMock())
    @patch("logging.Logger.debug", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    def test_async_async_fetch_sync_all_data__with_spider(self):
        from breathecode.career.actions import fetch_sync_all_data
        from logging import Logger

        model = self.bc.database.create(spider=spider, zyte_project=zyte_project, platform=platform)

        async_fetch_sync_all_data.delay({"spi_id": model["spider"].id})
        self.assertEqual(fetch_sync_all_data.call_args_list, [call(model.spider)])
        self.assertEqual(
            Logger.error.call_args_list,
            [
                call("Starting async_fetch_sync_all_data"),
                call("Starting async_fetch_sync_all_data in spider name getonboard"),
            ],
        )
