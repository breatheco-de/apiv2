from django.utils import timezone
from datetime import timedelta
from unittest.mock import MagicMock, call, patch
from ..mixins import JobsTestCase
from breathecode.tests.mocks import (
    REQUESTS_PATH,
    apply_requests_post_mock,
)

from ...tasks import async_run_spider

JOBS = [{
    'Searched_job': 'junior web developer',
    'Job_title': 'Pentester Cybersecurity',
    'Location': 'Remote (Chile, Venezuela)',
    'Company_name': 'Repite Employer',
    'Post_date': 'November 05, 2021',
    'Extract_date': '2022-01-30',
    'Job_description': 'Vuln exploitation Security reports',
    'Salary': 'Not supplied',
    'Tags': ['back-end', 'cybersecurity', 'english', 'pentesting', 'python'],
    'Apply_to': 'https://www.url.com/1',
    '_type': 'dict'
}, {
    'Searched_job': 'junior web developer',
    'Job_title': 'Pentester Cybersecurity',
    'Location': 'Remote (Chile)',
    'Company_name': 'Repite Employer',
    'Post_date': 'November 05, 2021',
    'Extract_date': '2022-01-30',
    'Job_description': 'Vuln exploitation Security reports',
    'Salary': 'Not supplied',
    'Tags': ['back-end', 'cybersecurity', 'english', 'pentesting', 'python'],
    'Apply_to': 'https://www.url.com/2',
    '_type': 'dict'
}]

spider = {'name': 'getonboard', 'zyte_spider_number': 3, 'zyte_job_number': 0}
zyte_project = {'zyte_api_key': 1234567, 'zyte_api_deploy': 11223344}
platform = {'name': 'getonboard'}


class RunSpiderTaskTestCase(JobsTestCase):
    """Test /answer"""
    """
    🔽🔽🔽 Without Task
    """
    @patch('breathecode.jobs.tasks.async_run_spider', MagicMock())
    @patch('logging.Logger.debug', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    def test_async_run_spider__without_tasks(self):
        from logging import Logger
        from breathecode.jobs.actions import save_data
        model = self.generate_models(spider=spider, zyte_project=zyte_project, platform=platform)

        async_run_spider.delay(model['spider'].id)
        self.assertEqual(self.bc.database.list_of('jobs.Spider'), [self.bc.format.to_dict(model.spider)])
        self.assertEqual(Logger.error.call_args_list, [
            call('Starting async_run_spider'),
            call('Starting async_run_spider'),
            call('Starting async_run_spider'),
            call('Starting async_run_spider'),
            call('Starting async_run_spider'),
            call('Starting async_run_spider')
        ])
