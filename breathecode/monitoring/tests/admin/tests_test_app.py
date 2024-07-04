from unittest.mock import patch, MagicMock, call
from django.http.request import HttpRequest

from ..mixins import MonitoringTestCase

# that 'import as' is thanks pytest think 'test_app' is one fixture
from ...admin import test_app as check_app
from ...models import Application

CURRENT_MOCK = MagicMock()
CURRENT_PATH = "breathecode.monitoring.tasks.monitor_app"


# This tests check functions are called, remember that this functions are
# tested in tests_monitor.py, we just need check that functions are called
# correctly
class AcademyCohortTestSuite(MonitoringTestCase):

    @patch(CURRENT_PATH, CURRENT_MOCK)
    def tests_test_app_length_0(self):
        request = HttpRequest()
        mock = CURRENT_MOCK.delay
        mock.call_args_list = []

        result = check_app(None, request, Application.objects.all())

        self.assertEqual(result, None)
        self.assertEqual(mock.call_args_list, [])

    @patch(CURRENT_PATH, CURRENT_MOCK)
    def tests_test_app_length_1(self):
        request = HttpRequest()
        mock = CURRENT_MOCK.delay
        mock.call_args_list = []

        models = [self.generate_models(application=True)]

        result = check_app(None, request, Application.objects.all())

        self.assertEqual(result, None)
        self.assertEqual(mock.call_args_list, [call(model["application"].id) for model in models])

    @patch(CURRENT_PATH, CURRENT_MOCK)
    def tests_test_app_length_3(self):
        request = HttpRequest()
        mock = CURRENT_MOCK.delay
        mock.call_args_list = []

        models = [self.generate_models(application=True) for _ in range(0, 3)]

        result = check_app(None, request, Application.objects.all())

        self.assertEqual(result, None)
        self.assertEqual(mock.call_args_list, [call(model["application"].id) for model in models])
