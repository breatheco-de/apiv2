from unittest.mock import patch, call, MagicMock
from ...actions import parse_date
from ..mixins import JobsTestCase
from datetime import datetime, timedelta, date
from breathecode.tests.mocks import (
    REQUESTS_PATH,
    apply_requests_post_mock,
)

spider = {'name': 'indeed', 'zyte_spider_number': 2, 'zyte_job_number': 0}
zyte_project = {
    'zyte_api_key': 1234567,
    'zyte_api_deploy': 11223344,
    'zyte_api_spider_number': 2,
    'zyte_api_last_job_number': 0
}
platform = {'name': 'indeed'}


class ActionRunSpiderTestCase(JobsTestCase):
    def test_parse_date__without_job(self):
        try:
            parse_date(None)
            assert False
        except Exception as e:
            self.assertEquals(str(e), ('data-job-none'))

    # @patch('breathecode.jobs.actions.parse_date', MagicMock())
    def test_parse_date__verify_format_published_date(self):
        job = {'published_date_raw': '30+ days ago'}
        model = self.bc.database.create(platform=platform, zyte_project=zyte_project, spider=spider, job=job)

        result = parse_date(model.job)
        result = result.published_date_processed
        result = f'{result.year}-{result.month}-{result.day}'
        expected = datetime.now() - timedelta(days=30)
        expected = f'{expected.year}-{expected.month}-{expected.day}'

        self.assertEquals(result, expected)

        job_1 = {'published_date_raw': 'Active 6 days ago'}
        model_1 = self.bc.database.create(spider=spider,
                                          zyte_project=zyte_project,
                                          platform=platform,
                                          job=job_1)

        result_1 = parse_date(model_1.job)
        result_1 = result_1.published_date_processed
        result_1 = f'{result_1.year}-{result_1.month}-{result_1.day}'
        expected_1 = datetime.now() - timedelta(days=6)
        expected_1 = f'{expected_1.year}-{expected_1.month}-{expected_1.day}'

        self.assertEquals(result_1, expected_1)

        job_2 = {'published_date_raw': 'July 17, 1977'}
        model_2 = self.bc.database.create(spider=spider,
                                          zyte_project=zyte_project,
                                          platform=platform,
                                          job=job_2)

        result_2 = parse_date(model_2.job)
        result_2 = result_2.published_date_processed
        result_2 = f'{result_2.year}-{result_2.month}-{result_2.day}'

        self.assertEquals(result_2, '1977-7-17')

        job_3 = {'published_date_raw': 'today'}
        model_3 = self.bc.database.create(spider=spider,
                                          zyte_project=zyte_project,
                                          platform=platform,
                                          job=job_3)

        result_3 = parse_date(model_3.job)
        result_3 = result_3.published_date_processed
        result_3 = f'{result_3.year}-{result_3.month}-{result_3.day}'
        expected_3 = datetime.now()
        expected_3 = f'{expected_3.year}-{expected_3.month}-{expected_3.day}'

        self.assertEquals(result_3, expected_3)
