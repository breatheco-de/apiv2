"""
Test /answer
"""

import re, urllib
from unittest.mock import patch, MagicMock, call
from django.urls.base import reverse_lazy
from rest_framework import status
from breathecode.notify.models import Hook
from breathecode.notify.tasks import async_deliver_hook

from breathecode.tests.mixins.legacy import LegacyAPITestCase
from breathecode.tests.mocks.requests import apply_requests_post_mock
from ..mixins import NotifyTestCase
import breathecode.services.slack.commands as commands
from breathecode.services.slack.client import Slack
from decimal import Decimal
from django.utils import timezone

UTC_NOW = timezone.now()


class TestAsyncDeliverHook(LegacyAPITestCase):
    """Test /answer"""

    def test_no_hook_id(self, fake, enable_hook_manager):
        enable_hook_manager()

        data = {
            fake.slug(): fake.slug(),
            fake.slug(): fake.slug(),
            fake.slug(): fake.slug(),
            "latitude": Decimal("25.758059600000000"),
            "longitude": Decimal("-80.377022000000000"),
            "date": timezone.now(),
        }

        url = fake.url()
        with patch("requests.post", apply_requests_post_mock([(201, url, {})])):
            res = async_deliver_hook(url, data)

        assert res == None
        assert self.bc.database.list_of("notify.Hook") == []

    def test_hook_not_found(self, fake, enable_hook_manager):
        enable_hook_manager()

        data = {
            fake.slug(): fake.slug(),
            fake.slug(): fake.slug(),
            fake.slug(): fake.slug(),
            "latitude": Decimal("25.758059600000000"),
            "longitude": Decimal("-80.377022000000000"),
            "date": timezone.now(),
        }

        url = fake.url()
        with patch("requests.post", apply_requests_post_mock([(201, url, {})])):
            with self.assertRaisesMessage(Hook.DoesNotExist, "Hook matching query does not exist."):
                async_deliver_hook(url, data, hook_id=1)

        assert self.bc.database.list_of("notify.Hook") == []

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_with_hook(self, fake, enable_hook_manager):
        enable_hook_manager()

        data = {
            fake.slug(): fake.slug(),
            fake.slug(): fake.slug(),
            fake.slug(): fake.slug(),
            "latitude": Decimal("25.758059600000000"),
            "longitude": Decimal("-80.377022000000000"),
            "date": timezone.now(),
        }

        model = self.bc.database.create(hook=1)

        url = fake.url()
        with patch("requests.post", apply_requests_post_mock([(201, url, {})])):
            res = async_deliver_hook(url, data, hook_id=1)

        assert res == None
        assert self.bc.database.list_of("notify.Hook") == [
            {
                **self.bc.format.to_dict(model.hook),
                "total_calls": model.hook.total_calls + 1,
                "last_call_at": UTC_NOW,
                "last_response_code": 201,
                "sample_data": [
                    {
                        **data,
                        "latitude": str(data["latitude"]),
                        "longitude": str(data["longitude"]),
                    },
                ],
            },
        ]

    def test_with_hook__returns_410(self, fake, enable_hook_manager):
        enable_hook_manager()

        data = {
            fake.slug(): fake.slug(),
            fake.slug(): fake.slug(),
            fake.slug(): fake.slug(),
            "latitude": Decimal("25.758059600000000"),
            "longitude": Decimal("-80.377022000000000"),
            "date": timezone.now(),
        }

        model = self.bc.database.create(hook=1)

        url = fake.url()
        with patch("requests.post", apply_requests_post_mock([(410, url, {})])):
            res = async_deliver_hook(url, data, hook_id=1)

        assert res == None
        assert self.bc.database.list_of("notify.Hook") == []
