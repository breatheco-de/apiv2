from unittest.mock import patch, call, MagicMock
from breathecode.tests.mocks.django_contrib import DJANGO_CONTRIB_PATH, apply_django_contrib_messages_mock
from breathecode.career.services import scraper_factory
from ..mixins import CareerTestCase


class ServicesGetClassScraperFactoryTestCase(CareerTestCase):

    @patch(DJANGO_CONTRIB_PATH["messages"], apply_django_contrib_messages_mock())
    @patch("django.contrib.messages.add_message", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    def test_return_false(self):

        from logging import Logger

        scraper_factory("motor")
        self.assertEqual(
            Logger.error.call_args_list,
            [call("There was an error import the library - No " "module named 'breathecode.career.services.motor'")],
        )

    def test_get_class_correctly(self):
        SPIDER = {"name": "getonboard", "zyte_spider_number": 1, "zyte_job_number": 0}
        ZYTE_PROJECT = {"zyte_api_key": 1234567, "zyte_api_deploy": 223344}
        PLATFORM = {"name": "getonboard"}

        model = self.bc.database.create(spider=SPIDER, zyte_project=ZYTE_PROJECT, platform=PLATFORM)

        result = scraper_factory("getonboard")
        self.assertEqual(result.__module__, "breathecode.career.services.getonboard")
        self.assertEqual(result.__qualname__, "GetonboardScraper")
