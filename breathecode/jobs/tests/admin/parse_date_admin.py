"""
Test /cohort/user
"""
from unittest.mock import patch, MagicMock, call
from breathecode.tests.mocks.django_contrib import DJANGO_CONTRIB_PATH, apply_django_contrib_messages_mock
from breathecode.jobs.models import Job
from breathecode.jobs.admin import parse_date_admin
from ..mixins import JobsTestCase
from django.http.request import HttpRequest


class RunSpiderAdminTestSuite(JobsTestCase):
    """Test /RunSpiderAdmin/"""
    """
    🔽🔽🔽 With zero Job
    """
    @patch(DJANGO_CONTRIB_PATH['messages'], apply_django_contrib_messages_mock())
    @patch('django.contrib.messages.add_message', MagicMock())
    @patch('breathecode.jobs.actions.parse_date', MagicMock())
    def test_parse_date_admin__with_zero_job(self):
        from breathecode.jobs.actions import parse_date
        request = HttpRequest()
        queryset = Job.objects.all()

        parse_date_admin(None, request, queryset)

        self.assertEqual(parse_date.call_args_list, [])

    """
    🔽🔽🔽 With one Spider
    """

    @patch(DJANGO_CONTRIB_PATH['messages'], apply_django_contrib_messages_mock())
    @patch('breathecode.jobs.actions.parse_date', MagicMock())
    def test_parse_date_admin__with_one_job(self):
        from breathecode.jobs.actions import parse_date
        from django.contrib import messages

        model = self.generate_models(job=True)

        request = HttpRequest()
        queryset = Job.objects.all()

        parse_date_admin(None, request, queryset)

        self.assertEqual(parse_date.call_args_list, [call(model.job)])

    """
    🔽🔽🔽 With two Spider
    """

    @patch(DJANGO_CONTRIB_PATH['messages'], apply_django_contrib_messages_mock())
    @patch('breathecode.jobs.actions.parse_date', MagicMock())
    def test_parse_date_admin__with_two_jobs(self):
        from breathecode.jobs.actions import parse_date
        from django.contrib import messages

        model_1 = self.generate_models(job=True)
        model_2 = self.generate_models(job=True)

        request = HttpRequest()
        queryset = Job.objects.all()

        parse_date_admin(None, request, queryset)

        self.assertEqual(parse_date.call_args_list, [call(model_1.job), call(model_2.job)])
