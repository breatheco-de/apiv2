"""
Test /answer
"""

from django.utils import timezone
from datetime import timedelta
from unittest.mock import MagicMock, call, patch
from ..mixins import JobsTestCase
from breathecode.tests.mocks import (
    REQUESTS_PATH,
    apply_requests_post_mock,
)

from ...tasks import async_fetch_sync_all_data

spider = {'name': 'getonboard', 'zyte_spider_number': 3, 'zyte_job_number': 0}
zyte_project = {'zyte_api_key': 1234567, 'zyte_api_deploy': 11223344}
platform = {'name': 'getonboard'}


class AsyncFetchSyncAllDataTaskTestCase(JobsTestCase):
    """Test /answer"""
    """
    🔽🔽🔽 Without Task
    """
    @patch('breathecode.jobs.tasks.async_fetch_sync_all_data', MagicMock())
    @patch('logging.Logger.debug', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    def test_async_async_fetch_sync_all_data__without_tasks(self):
        from logging import Logger
        from breathecode.jobs.actions import save_data
        model = self.bc.database.create(spider=spider, zyte_project=zyte_project, platform=platform)

        async_fetch_sync_all_data.delay(model.spider.id)
        self.assertEqual(self.bc.database.list_of('jobs.Spider'), [self.bc.format.to_dict(model.spider)])
        self.assertEqual(Logger.error.call_args_list, [
            call('Starting async_fetch_sync_all_data'),
            call('Starting async_fetch_sync_all_data'),
            call('Starting async_fetch_sync_all_data'),
            call('Starting async_fetch_sync_all_data'),
            call('Starting async_fetch_sync_all_data'),
            call('Starting async_fetch_sync_all_data')
        ])
