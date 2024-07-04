from unittest.mock import patch, MagicMock, call
from breathecode.tests.mocks.django_contrib import DJANGO_CONTRIB_PATH, apply_django_contrib_messages_mock
from breathecode.career.models import Spider
from breathecode.career.admin import run_spider_admin
from ..mixins import CareerTestCase
from django.http.request import HttpRequest


class RunSpiderAdminTestSuite(CareerTestCase):

    @patch(DJANGO_CONTRIB_PATH["messages"], apply_django_contrib_messages_mock())
    @patch("django.contrib.messages.add_message", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.career.actions.run_spider", MagicMock(side_effect=Exception("They killed kenny")))
    def test_run_spider_admin__with_zero_spider_logger_error(self):
        from breathecode.career.actions import run_spider
        from logging import Logger

        model = self.bc.database.create(spider=1)
        request = HttpRequest()
        queryset = Spider.objects.all()

        run_spider_admin(None, request, queryset)
        self.assertEqual(
            Logger.error.call_args_list, [call("There was an error retriving the spider They killed kenny")]
        )

    @patch(DJANGO_CONTRIB_PATH["messages"], apply_django_contrib_messages_mock())
    @patch("django.contrib.messages.add_message", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.career.actions.run_spider", MagicMock(side_effect=Exception("They killed kenny")))
    def test_run_spider_admin__with_zero_spider(self):
        from breathecode.career.actions import run_spider
        from logging import Logger

        model = self.bc.database.create(spider=1)
        request = HttpRequest()
        queryset = Spider.objects.all()

        run_spider_admin(None, request, queryset)

        self.assertEqual(
            Logger.error.call_args_list, [call("There was an error retriving the spider They killed kenny")]
        )
        self.assertEqual(run_spider.call_args_list, [call(model.spider)])

    @patch(DJANGO_CONTRIB_PATH["messages"], apply_django_contrib_messages_mock())
    @patch("breathecode.career.actions.run_spider", MagicMock())
    def test_run_spider_admin__with_one_spider(self):
        from breathecode.career.actions import run_spider
        from django.contrib import messages

        model = self.bc.database.create(spider=1)

        request = HttpRequest()
        queryset = Spider.objects.all()

        run_spider_admin(None, request, queryset)

        self.assertEqual(run_spider.call_args_list, [call(model.spider)])

    @patch(DJANGO_CONTRIB_PATH["messages"], apply_django_contrib_messages_mock())
    @patch("breathecode.career.actions.run_spider", MagicMock())
    def test_run_spider_admin__with_two_spiders(self):
        from breathecode.career.actions import run_spider
        from django.contrib import messages

        model_1 = self.bc.database.create(spider=1)
        model_2 = self.bc.database.create(spider=1)

        request = HttpRequest()
        queryset = Spider.objects.all()

        run_spider_admin(None, request, queryset)

        self.assertEqual(run_spider.call_args_list, [call(model_1.spider), call(model_2.spider)])
