"""
Tasks tests
"""
from unittest.mock import patch, call
from ...actions import parse_date
from ..mixins import JobsTestCase
from datetime import datetime, timedelta, date
from breathecode.tests.mocks import (
    REQUESTS_PATH,
    apply_requests_post_mock,
)


class ActionRunSpiderTestCase(JobsTestCase):
    def test_parse_date__without_job(self):
        """Test /parse_date without spider"""
        try:
            parse_date(None)
            assert False
        except Exception as e:
            self.assertEquals(str(e), ('data-job-none'))

    def test_parse_date__verify_format_published_date(self):
        """Test /parse_date verify format published date"""
        model = self.generate_models(job=True, job_kwargs={'published_date_raw': '30+ days ago'})

        result = parse_date(model.job)
        result = result.published_date_processed
        result = f'{result.year}-{result.month}-{result.day}'
        expected = datetime.now() - timedelta(days=30)
        expected = f'{expected.year}-{expected.month}-{expected.day}'

        self.assertEquals(result, expected)

        model_1 = self.generate_models(job=True, job_kwargs={'published_date_raw': 'Active 6 days ago'})

        result_1 = parse_date(model_1.job)
        result_1 = result_1.published_date_processed
        result_1 = f'{result_1.year}-{result_1.month}-{result_1.day}'
        expected_1 = datetime.now() - timedelta(days=6)
        expected_1 = f'{expected_1.year}-{expected_1.month}-{expected_1.day}'

        self.assertEquals(result_1, expected_1)

        model_2 = self.generate_models(job=True, job_kwargs={'published_date_raw': 'July 17, 1977'})

        result_2 = parse_date(model_2.job)
        result_2 = result_2.published_date_processed
        result_2 = f'{result_2.year}-{result_2.month}-{result_2.day}'

        self.assertEquals(result_2, '1977-7-17')
