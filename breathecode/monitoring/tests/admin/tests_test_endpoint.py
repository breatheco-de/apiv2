from unittest.mock import patch, MagicMock, call
from django.http.request import HttpRequest

from ..mixins import MonitoringTestCase

# that 'import as' is thanks pytest think 'test_endpoint' is one fixture
from ...admin import test_endpoint as check_endpoint
from ...models import Endpoint

CURRENT_MOCK = MagicMock()
CURRENT_PATH = "breathecode.monitoring.tasks.test_endpoint"


# This tests check functions are called, remember that this functions are
# tested in tests_monitor.py, we just need check that functions are called
# correctly
class AcademyCohortTestSuite(MonitoringTestCase):

    @patch(CURRENT_PATH, CURRENT_MOCK)
    def tests_test_endpoint_length_0(self):
        request = HttpRequest()
        mock = CURRENT_MOCK.delay
        mock.call_args_list = []

        result = check_endpoint(None, request, Endpoint.objects.all())

        self.assertEqual(result, None)
        self.assertEqual(mock.call_args_list, [])

    @patch(CURRENT_PATH, CURRENT_MOCK)
    def tests_test_endpoint_length_1(self):
        request = HttpRequest()
        mock = CURRENT_MOCK.delay
        mock.call_args_list = []

        models = [self.generate_models(endpoint=True)]

        result = check_endpoint(None, request, Endpoint.objects.all())

        self.assertEqual(result, None)
        self.assertEqual(mock.call_args_list, [call(model["endpoint"].id) for model in models])

    @patch(CURRENT_PATH, CURRENT_MOCK)
    def tests_test_endpoint_length_3(self):
        request = HttpRequest()
        mock = CURRENT_MOCK.delay
        mock.call_args_list = []

        models = [self.generate_models(endpoint=True) for _ in range(0, 3)]

        result = check_endpoint(None, request, Endpoint.objects.all())

        self.assertEqual(result, None)
        self.assertEqual(mock.call_args_list, [call(model["endpoint"].id) for model in models])
