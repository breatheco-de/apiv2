from datetime import timedelta
from django.utils import timezone
from unittest.mock import patch, MagicMock, call
from django.http.request import HttpRequest

from ..mixins import MonitoringTestCase
from ...admin import run_single_script
from ...models import MonitorScript

RUN_SCRIPT_MOCK = MagicMock()
RUN_SCRIPT_PATH = "breathecode.monitoring.tasks.execute_scripts"


# This tests check functions are called, remember that this functions are
# tested in tests_monitor.py, we just need check that functions are called
# correctly
class AcademyCohortTestSuite(MonitoringTestCase):

    @patch(RUN_SCRIPT_PATH, RUN_SCRIPT_MOCK)
    def tests_run_single_script_length_0(self):
        request = HttpRequest()
        mock_run_script = RUN_SCRIPT_MOCK.delay
        mock_run_script.call_args_list = []

        result = run_single_script(None, request, MonitorScript.objects.all())

        self.assertEqual(result, None)
        self.assertEqual(mock_run_script.call_args_list, [])

    @patch(RUN_SCRIPT_PATH, RUN_SCRIPT_MOCK)
    def tests_run_single_script_length_1(self):
        request = HttpRequest()
        mock_run_script = RUN_SCRIPT_MOCK.delay
        mock_run_script.call_args_list = []

        models = [self.generate_models(monitor_script=True)]

        result = run_single_script(None, request, MonitorScript.objects.all())

        self.assertEqual(result, None)
        self.assertEqual(mock_run_script.call_args_list, [call(model["monitor_script"].id) for model in models])

    @patch(RUN_SCRIPT_PATH, RUN_SCRIPT_MOCK)
    def tests_run_single_script_length_3(self):
        request = HttpRequest()
        mock_run_script = RUN_SCRIPT_MOCK.delay
        mock_run_script.call_args_list = []

        models = [self.generate_models(monitor_script=True) for _ in range(0, 3)]

        result = run_single_script(None, request, MonitorScript.objects.all())

        self.assertEqual(result, None)
        self.assertEqual(mock_run_script.call_args_list, [call(model["monitor_script"].id) for model in models])
