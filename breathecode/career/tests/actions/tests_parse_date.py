from unittest.mock import patch, call, MagicMock
from breathecode.tests.mocks.django_contrib import DJANGO_CONTRIB_PATH, apply_django_contrib_messages_mock
from ...actions import get_was_published_date_from_string
from ..mixins import CareerTestCase
from django.utils import timezone
from datetime import timedelta
from breathecode.tests.mocks import (
    REQUESTS_PATH,
    apply_requests_post_mock,
)

spider = {"name": "indeed", "zyte_spider_number": 2, "zyte_job_number": 0}
zyte_project = {
    "zyte_api_key": 1234567,
    "zyte_api_deploy": 11223344,
    "zyte_api_spider_number": 2,
    "zyte_api_last_job_number": 0,
}
platform = {"name": "indeed"}


class ActionRunSpiderTestCase(CareerTestCase):

    @patch(DJANGO_CONTRIB_PATH["messages"], apply_django_contrib_messages_mock())
    @patch("django.contrib.messages.add_message", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    def test_get_was_published_date_from_string__without_job(self):
        from logging import Logger

        try:
            get_was_published_date_from_string(None)
            assert False
        except Exception as e:
            self.assertEqual(str(e), ("data-job-none"))
            self.assertEqual(
                Logger.error.call_args_list,
                [
                    call("First you must specify a job (get_was_published_date_from_string)"),
                ],
            )

    def test_get_was_published_date_from_string__whith_x_days_ago(self):
        job = {"published_date_raw": "30+ days ago"}
        model = self.bc.database.create(platform=platform, zyte_project=zyte_project, spider=spider, job=job)

        result = get_was_published_date_from_string(model.job)
        result = result.published_date_processed
        result = f"{result.year}-{result.month}-{result.day}"
        expected = timezone.now() - timedelta(days=30)
        expected = f"{expected.year}-{expected.month}-{expected.day}"

        self.assertEqual(result, expected)

    def test_get_was_published_date_from_string__whith_active_x_days_ago(self):
        job = {"published_date_raw": "Active 6 days ago"}
        model = self.bc.database.create(spider=spider, zyte_project=zyte_project, platform=platform, job=job)

        result = get_was_published_date_from_string(model.job)
        result = result.published_date_processed
        result = f"{result.year}-{result.month}-{result.day}"
        expected = timezone.now() - timedelta(days=6)
        expected = f"{expected.year}-{expected.month}-{expected.day}"

        self.assertEqual(result, expected)

    def test_get_was_published_date_from_string__whith_month_day_year(self):
        job = {"published_date_raw": "July 17, 1977"}
        model = self.bc.database.create(spider=spider, zyte_project=zyte_project, platform=platform, job=job)

        result = get_was_published_date_from_string(model.job)
        result = result.published_date_processed
        result = f"{result.year}-{result.month}-{result.day}"

        self.assertEqual(result, "1977-7-17")

    def test_get_was_published_date_from_string__whith_today(self):
        job = {"published_date_raw": "today"}
        model = self.bc.database.create(spider=spider, zyte_project=zyte_project, platform=platform, job=job)

        result = get_was_published_date_from_string(model.job)
        result = result.published_date_processed
        result = f"{result.year}-{result.month}-{result.day}"
        expected = timezone.now()
        expected = f"{expected.year}-{expected.month}-{expected.day}"

        self.assertEqual(result, expected)
