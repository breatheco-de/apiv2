"""
Collections of mixins used to login in authorize microservice
"""

from rest_framework.test import APITestCase
from breathecode.tests.mixins import (
    GenerateModelsMixin,
    CacheMixin,
    GenerateQueriesMixin,
    OldBreathecodeMixin,
    DatetimeMixin,
    BreathecodeMixin,
)


class EventTestCase(
    APITestCase,
    GenerateModelsMixin,
    CacheMixin,
    GenerateQueriesMixin,
    OldBreathecodeMixin,
    DatetimeMixin,
    BreathecodeMixin,
):
    """AdmissionsTestCase with auth methods"""

    def setUp(self):
        self.generate_queries()
        self.reset_old_breathecode_calls()
        self.set_test_instance(self)

    def tearDown(self):
        self.clear_cache()

    def data(self, action="test", url="https://www.eventbriteapi.com/v3/test"):
        return {
            "api_url": url,
            "config": {
                "user_id": "123456789012",
                "action": action,
                "webhook_id": "1234567",
                "endpoint_url": "https://something.io/eventbrite/webhook",
            },
        }

    def headers(self, event="test"):
        return {
            "X-Eventbrite-Event": event,
            "Accept": "text/plain",
            "User-Agent": "Eventbrite Hookshot 12345c6",
            "X-Eventbrite-Delivery": "1234567",
            "Content-type": "application/json",
            "User-ID-Sender": "123456789012",
        }
