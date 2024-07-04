from unittest.mock import patch, MagicMock, call
from breathecode.tests.mocks.django_contrib import DJANGO_CONTRIB_PATH, apply_django_contrib_messages_mock
from breathecode.career.models import Job
from breathecode.career.admin import get_was_published_date_from_string_admin
from ..mixins import CareerTestCase
from django.http.request import HttpRequest


class ParseDateAdminTestSuite(CareerTestCase):

    @patch(DJANGO_CONTRIB_PATH["messages"], apply_django_contrib_messages_mock())
    @patch("django.contrib.messages.add_message", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch(
        "breathecode.career.actions.get_was_published_date_from_string",
        MagicMock(side_effect=Exception("They killed kenny")),
    )
    def test_get_was_published_date_from_string_admin__with_zero_job(self):
        from breathecode.career.actions import get_was_published_date_from_string
        from logging import Logger

        model = self.bc.database.create(job=1)
        request = HttpRequest()
        queryset = Job.objects.all()

        get_was_published_date_from_string_admin(None, request, queryset)
        self.assertEqual(Logger.error.call_args_list, [call("There was an error retriving the jobs They killed kenny")])
        self.assertEqual(get_was_published_date_from_string.call_args_list, [call(model.job)])

    @patch(DJANGO_CONTRIB_PATH["messages"], apply_django_contrib_messages_mock())
    @patch("breathecode.career.actions.get_was_published_date_from_string", MagicMock())
    def test_get_was_published_date_from_string_admin__with_one_job(self):
        from breathecode.career.actions import get_was_published_date_from_string
        from django.contrib import messages

        model = self.bc.database.create(job=1)

        request = HttpRequest()
        queryset = Job.objects.all()

        get_was_published_date_from_string_admin(None, request, queryset)
        self.assertEqual(get_was_published_date_from_string.call_args_list, [call(model.job)])

    @patch(DJANGO_CONTRIB_PATH["messages"], apply_django_contrib_messages_mock())
    @patch("breathecode.career.actions.get_was_published_date_from_string", MagicMock())
    def test_get_was_published_date_from_string_admin__with_two_jobs(self):
        from breathecode.career.actions import get_was_published_date_from_string
        from django.contrib import messages

        model_1 = self.bc.database.create(job=1)
        model_2 = self.bc.database.create(job=1)

        request = HttpRequest()
        queryset = Job.objects.all()

        get_was_published_date_from_string_admin(None, request, queryset)

        self.assertEqual(get_was_published_date_from_string.call_args_list, [call(model_1.job), call(model_2.job)])
