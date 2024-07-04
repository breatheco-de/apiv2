from unittest.mock import patch, MagicMock, call
from django.http.request import HttpRequest
from django.utils import timezone

from ..mixins import MonitoringTestCase
from ...admin import pause_for_one_day
from ...models import Endpoint


# This tests check functions are called, remember that this functions are
# tested in tests_monitor.py, we just need check that functions are called
# correctly
class AcademyCohortTestSuite(MonitoringTestCase):

    def tests_pause_for_one_day_length_0(self):
        request = HttpRequest()

        result = pause_for_one_day(None, request, Endpoint.objects.all())

        self.assertEqual(result, None)
        self.assertEqual(self.all_endpoint_dict(), [])

    def tests_pause_for_one_day_length_1(self):
        request = HttpRequest()

        models = [self.generate_models(endpoint=True)]
        result = pause_for_one_day(None, request, Endpoint.objects.all())

        self.assertEqual(result, None)

        endpoints = [
            {**endpoint, "paused_until": None}
            for endpoint in self.all_endpoint_dict()
            if self.assertDatetime(endpoint["paused_until"])
        ]
        self.assertEqual(
            endpoints, [{**self.model_to_dict(model, "endpoint"), "frequency_in_minutes": 30.0} for model in models]
        )

    def tests_pause_for_one_day_length_3(self):
        request = HttpRequest()

        models = [self.generate_models(endpoint=True) for _ in range(0, 3)]
        result = pause_for_one_day(None, request, Endpoint.objects.all())

        self.assertEqual(result, None)

        endpoints = [
            {**endpoint, "paused_until": None}
            for endpoint in self.all_endpoint_dict()
            if self.assertDatetime(endpoint["paused_until"])
        ]
        self.assertEqual(
            endpoints, [{**self.model_to_dict(model, "endpoint"), "frequency_in_minutes": 30.0} for model in models]
        )
