"""
Test /luma/webhook
"""

from unittest.mock import MagicMock, call, patch

from django.urls.base import reverse_lazy
from rest_framework import status

from breathecode.tests.mocks import apply_old_breathecode_requests_request_mock
from breathecode.tests.mocks.luma import (
    LUMA_GUEST_REGISTERED,
    LUMA_GUEST_UPDATED,
    LUMA_EVENT_ID,
    LUMA_WEBHOOK_SECRET,
    sign_luma_request,
)

from ..mixins import EventTestCase


class LumaWebhookTestSuite(EventTestCase):
    """Test /luma/webhook"""

    def test_luma_webhook_without_data(self):
        url = reverse_lazy("events:luma_webhook_id", kwargs={"organization_id": 1})
        response = self.client.post(url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.all_luma_webhook_dict(), [])

    def test_luma_webhook_invalid_signature(self):
        model = self.generate_models(
            organization=True,
            organization_kwargs={"luma_webhook_secret": LUMA_WEBHOOK_SECRET},
        )
        url = reverse_lazy("events:luma_webhook_id", kwargs={"organization_id": model.organization.id})
        body, headers = sign_luma_request("whsec_wrong_secret", LUMA_GUEST_REGISTERED)

        response = self.client.post(url, body, headers=headers, content_type="application/json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.all_luma_webhook_dict(), [])

    @patch("breathecode.marketing.tasks.add_event_tags_to_student", MagicMock())
    @patch("requests.request", apply_old_breathecode_requests_request_mock())
    def test_luma_webhook_guest_registered(self):
        from breathecode.marketing.tasks import add_event_tags_to_student

        model = self.generate_models(
            organization=True,
            organization_kwargs={
                "luma_webhook_secret": LUMA_WEBHOOK_SECRET,
                "luma_calendar_id": "cal-123",
            },
            event=True,
            event_kwargs={"luma_id": LUMA_EVENT_ID, "lang": "en"},
            active_campaign_academy=True,
            automation=True,
            user=True,
            academy=True,
            active_campaign_academy_kwargs={"ac_url": "https://old.hardcoded.breathecode.url"},
            user_kwargs={"email": "john.smith@example.com", "first_name": "John", "last_name": "Smith"},
        )

        url = reverse_lazy("events:luma_webhook_id", kwargs={"organization_id": model.organization.id})
        body, headers = sign_luma_request(LUMA_WEBHOOK_SECRET, LUMA_GUEST_REGISTERED)
        response = self.client.post(url, body, headers=headers, content_type="application/json")

        self.assertEqual(response.content, b"ok")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        webhook_dicts = self.all_luma_webhook_dict()
        for webhook_dict in webhook_dicts:
            del webhook_dict["payload"]
        self.assertEqual(
            webhook_dicts,
            [
                {
                    "attendee_id": 1,
                    "event_id": 1,
                    "id": 1,
                    "luma_guest_id": "gst-abc123",
                    "organization_id": "1",
                    "status": "DONE",
                    "status_text": "OK",
                    "type": "guest.registered",
                    "webhook_id": "wh_evt_test_123",
                }
            ],
        )

        self.assertEqual(
            self.all_event_checkin_dict(),
            [
                {
                    "attendee_id": 1,
                    "attended_at": None,
                    "email": "john.smith@example.com",
                    "event_id": 1,
                    "id": 1,
                    "luma_guest_id": "gst-abc123",
                    "status": "PENDING",
                    "utm_campaign": None,
                    "utm_medium": None,
                    "utm_source": "luma",
                    "utm_url": None,
                }
            ],
        )
        self.assertEqual(
            add_event_tags_to_student.delay.call_args_list,
            [call(model.event.id, email=model.user.email)],
        )

    @patch("breathecode.marketing.tasks.add_event_tags_to_student", MagicMock())
    @patch("requests.request", apply_old_breathecode_requests_request_mock())
    def test_luma_webhook_guest_registered_without_linked_event(self):
        model = self.generate_models(
            organization=True,
            organization_kwargs={"luma_webhook_secret": LUMA_WEBHOOK_SECRET},
            academy=True,
        )

        url = reverse_lazy("events:luma_webhook_id", kwargs={"organization_id": model.organization.id})
        body, headers = sign_luma_request(LUMA_WEBHOOK_SECRET, LUMA_GUEST_REGISTERED)
        response = self.client.post(url, body, headers=headers, content_type="application/json")

        self.assertEqual(response.content, b"ok")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        webhook_dicts = self.all_luma_webhook_dict()
        self.assertEqual(webhook_dicts[0]["status"], "ERROR")
        self.assertIn("event doesn't exist", webhook_dicts[0]["status_text"])

    @patch("breathecode.marketing.tasks.add_event_tags_to_student", MagicMock())
    @patch("requests.request", apply_old_breathecode_requests_request_mock())
    def test_luma_webhook_guest_updated_checkin(self):
        model = self.generate_models(
            organization=True,
            organization_kwargs={"luma_webhook_secret": LUMA_WEBHOOK_SECRET},
            event=True,
            event_kwargs={"luma_id": LUMA_EVENT_ID, "lang": "en"},
            active_campaign_academy=True,
            automation=True,
            user=True,
            academy=True,
            event_checkin=True,
            event_checkin_kwargs={
                "email": "john.smith@example.com",
                "luma_guest_id": "gst-abc123",
                "status": "PENDING",
            },
            user_kwargs={"email": "john.smith@example.com"},
        )

        url = reverse_lazy("events:luma_webhook_id", kwargs={"organization_id": model.organization.id})
        body, headers = sign_luma_request(LUMA_WEBHOOK_SECRET, LUMA_GUEST_UPDATED)
        response = self.client.post(url, body, headers=headers, content_type="application/json")

        self.assertEqual(response.content, b"ok")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        checkin = self.all_event_checkin_dict()[0]
        self.assertEqual(checkin["status"], "DONE")
        self.assertIsNotNone(checkin["attended_at"])

        webhook_dicts = self.all_luma_webhook_dict()
        self.assertEqual(webhook_dicts[0]["status"], "DONE")
        self.assertEqual(webhook_dicts[0]["type"], "guest.updated")

    @patch("breathecode.marketing.tasks.add_event_tags_to_student", MagicMock())
    @patch("requests.request", apply_old_breathecode_requests_request_mock())
    def test_luma_webhook_guest_registered_skips_non_approved(self):
        from breathecode.marketing.tasks import add_event_tags_to_student

        model = self.generate_models(
            organization=True,
            organization_kwargs={"luma_webhook_secret": LUMA_WEBHOOK_SECRET},
            event=True,
            event_kwargs={"luma_id": LUMA_EVENT_ID, "lang": "en"},
            academy=True,
        )

        payload = {
            "type": "guest.registered",
            "data": {
                **LUMA_GUEST_REGISTERED["data"],
                "approval_status": "pending_approval",
            },
        }

        url = reverse_lazy("events:luma_webhook_id", kwargs={"organization_id": model.organization.id})
        body, headers = sign_luma_request(LUMA_WEBHOOK_SECRET, payload)
        response = self.client.post(url, body, headers=headers, content_type="application/json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_event_checkin_dict(), [])
        self.assertEqual(add_event_tags_to_student.delay.call_args_list, [])

        webhook_dicts = self.all_luma_webhook_dict()
        self.assertEqual(webhook_dicts[0]["status"], "DONE")
        self.assertIn("skipped", webhook_dicts[0]["status_text"])
