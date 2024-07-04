"""
Test /eventbrite/webhook
"""

from unittest.mock import MagicMock, call, patch

import requests
from django.urls.base import reverse_lazy
from rest_framework import status

import breathecode.events.actions as actions
from breathecode.tests.mocks import (
    EVENTBRITE_ORDER_URL,
    apply_eventbrite_requests_post_mock,
    apply_old_breathecode_requests_request_mock,
)
from breathecode.tests.mocks.eventbrite.constants.event import EVENTBRITE_EVENT
from breathecode.tests.mocks.requests import REQUESTS_PATH, apply_requests_get_mock

from ..mixins import EventTestCase

eventbrite_url = "https://www.eventbriteapi.com/v3/events/1/"
eventbrite_url_with_query = eventbrite_url + "?expand=organizer,venue"


def update_or_create_event_mock(raise_error=False):

    def update_or_create_event(self, *args, **kwargs):
        if raise_error:
            raise Exception("Random error in creating")

    return MagicMock(side_effect=update_or_create_event)


# FIXME: this file have performance issues often
class EventbriteWebhookTestSuite(EventTestCase):
    """Test /eventbrite/webhook"""

    @patch("requests.get", apply_eventbrite_requests_post_mock())
    @patch("time.sleep", MagicMock())
    def test_eventbrite_webhook_without_data(self):
        """Test /eventbrite/webhook without auth"""
        url = reverse_lazy("events:eventbrite_webhook_id", kwargs={"organization_id": 1})
        response = self.client.post(url, {}, headers=self.headers(), format="json")
        content = response.content

        self.assertEqual(content, b"ok")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_event_checkin_dict(), [])
        self.assertEqual(self.all_eventbrite_webhook_dict(), [])
        self.check_old_breathecode_calls({}, [])

    """
    🔽🔽🔽 order.placed
    """

    @patch("requests.get", apply_eventbrite_requests_post_mock())
    @patch("breathecode.marketing.tasks.add_event_tags_to_student", MagicMock())
    @patch("time.sleep", MagicMock())
    def test_eventbrite_webhook_without_organization(self):
        from breathecode.marketing.tasks import add_event_tags_to_student

        url = reverse_lazy("events:eventbrite_webhook_id", kwargs={"organization_id": 1})
        response = self.client.post(
            url, self.data("order.placed", EVENTBRITE_ORDER_URL), headers=self.headers("order.placed"), format="json"
        )
        content = response.content

        self.assertEqual(content, b"ok")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_event_checkin_dict(), [])
        self.assertEqual(
            self.all_eventbrite_webhook_dict(),
            [
                {
                    "action": "order.placed",
                    "api_url": "https://www.eventbriteapi.com/v3/events/1/orders/1/",
                    "endpoint_url": "https://something.io/eventbrite/webhook",
                    "id": 1,
                    "payload": None,
                    "event_id": None,
                    "attendee_id": None,
                    "organization_id": "1",
                    "status": "ERROR",
                    "status_text": "Organization 1 doesn't exist",
                    "user_id": "123456789012",
                    "webhook_id": "1234567",
                }
            ],
        )
        self.check_old_breathecode_calls({}, [])
        self.assertEqual(add_event_tags_to_student.delay.call_args_list, [])

    @patch("requests.get", apply_eventbrite_requests_post_mock())
    @patch("breathecode.marketing.tasks.add_event_tags_to_student", MagicMock())
    @patch("time.sleep", MagicMock())
    def test_eventbrite_webhook_without_academy(self):
        from breathecode.marketing.tasks import add_event_tags_to_student

        model = self.generate_models(organization=True)
        url = reverse_lazy("events:eventbrite_webhook_id", kwargs={"organization_id": 1})
        response = self.client.post(
            url, self.data("order.placed", EVENTBRITE_ORDER_URL), headers=self.headers("order.placed"), format="json"
        )
        content = response.content

        self.assertEqual(content, b"ok")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_event_checkin_dict(), [])

        db = self.bc.database.list_of("events.EventbriteWebhook")
        self.assertRegex(db[0]["status_text"], r"Exception: Organization not have one Academy\n")
        self.bc.check.partial_equality(
            db,
            [
                {
                    "action": "order.placed",
                    "api_url": "https://www.eventbriteapi.com/v3/events/1/orders/1/",
                    "endpoint_url": "https://something.io/eventbrite/webhook",
                    "id": 1,
                    "organization_id": "1",
                    "status": "ERROR",
                    "user_id": "123456789012",
                    "webhook_id": "1234567",
                }
            ],
        )
        self.check_old_breathecode_calls(model, [])
        self.assertEqual(add_event_tags_to_student.delay.call_args_list, [])

    @patch("requests.get", apply_eventbrite_requests_post_mock())
    @patch("breathecode.marketing.tasks.add_event_tags_to_student", MagicMock())
    @patch("time.sleep", MagicMock())
    def test_eventbrite_webhook_without_event(self):
        from breathecode.marketing.tasks import add_event_tags_to_student

        model = self.generate_models(organization=True, academy=True)
        url = reverse_lazy("events:eventbrite_webhook_id", kwargs={"organization_id": 1})
        response = self.client.post(
            url, self.data("order.placed", EVENTBRITE_ORDER_URL), headers=self.headers("order.placed"), format="json"
        )
        content = response.content

        self.assertEqual(content, b"ok")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_event_checkin_dict(), [])

        db = self.bc.database.list_of("events.EventbriteWebhook")
        self.assertRegex(db[0]["status_text"], r"Exception: event doesn\'t exist\n")
        self.bc.check.partial_equality(
            db,
            [
                {
                    "action": "order.placed",
                    "api_url": "https://www.eventbriteapi.com/v3/events/1/orders/1/",
                    "endpoint_url": "https://something.io/eventbrite/webhook",
                    "id": 1,
                    "organization_id": "1",
                    "status": "ERROR",
                    "user_id": "123456789012",
                    "webhook_id": "1234567",
                }
            ],
        )
        self.check_old_breathecode_calls(model, [])
        self.assertEqual(add_event_tags_to_student.delay.call_args_list, [])

    @patch("requests.get", apply_eventbrite_requests_post_mock())
    @patch("breathecode.marketing.tasks.add_event_tags_to_student", MagicMock())
    @patch("time.sleep", MagicMock())
    def test_eventbrite_webhook_with_event_without_eventbrite_id(self):
        from breathecode.marketing.tasks import add_event_tags_to_student

        model = self.generate_models(organization=True, academy=True, event=True)
        url = reverse_lazy("events:eventbrite_webhook_id", kwargs={"organization_id": 1})
        response = self.client.post(
            url, self.data("order.placed", EVENTBRITE_ORDER_URL), headers=self.headers("order.placed"), format="json"
        )
        content = response.content

        self.assertEqual(content, b"ok")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_event_checkin_dict(), [])

        db = self.bc.database.list_of("events.EventbriteWebhook")
        self.assertRegex(db[0]["status_text"], r"Exception: event doesn\'t exist\n")
        self.bc.check.partial_equality(
            db,
            [
                {
                    "action": "order.placed",
                    "api_url": "https://www.eventbriteapi.com/v3/events/1/orders/1/",
                    "endpoint_url": "https://something.io/eventbrite/webhook",
                    "id": 1,
                    "organization_id": "1",
                    "status": "ERROR",
                    "user_id": "123456789012",
                    "webhook_id": "1234567",
                }
            ],
        )
        self.check_old_breathecode_calls(model, [])
        self.assertEqual(add_event_tags_to_student.delay.call_args_list, [])

    @patch("requests.get", apply_eventbrite_requests_post_mock())
    @patch("breathecode.marketing.tasks.add_event_tags_to_student", MagicMock())
    @patch("time.sleep", MagicMock())
    def test_eventbrite_webhook_without_active_campaign_academy(self):
        from breathecode.marketing.tasks import add_event_tags_to_student

        model = self.generate_models(
            organization=True, academy=True, event=True, event_kwargs={"eventbrite_id": 1}, attendee=True
        )
        url = reverse_lazy("events:eventbrite_webhook_id", kwargs={"organization_id": 1})
        response = self.client.post(
            url, self.data("order.placed", EVENTBRITE_ORDER_URL), headers=self.headers("order.placed"), format="json"
        )
        content = response.content

        self.assertEqual(content, b"ok")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        db = self.bc.database.list_of("events.EventbriteWebhook")
        self.assertRegex(db[0]["status_text"], r"Exception: ActiveCampaignAcademy doesn\'t exist\n")

        self.bc.check.partial_equality(
            db,
            [
                {
                    "action": "order.placed",
                    "api_url": "https://www.eventbriteapi.com/v3/events/1/orders/1/",
                    "endpoint_url": "https://something.io/eventbrite/webhook",
                    "id": 1,
                    "organization_id": "1",
                    "status": "ERROR",
                    "user_id": "123456789012",
                    "webhook_id": "1234567",
                }
            ],
        )

        self.assertEqual(
            self.all_event_checkin_dict(),
            [
                {
                    "attendee_id": None,
                    "email": "john.smith@example.com",
                    "event_id": 1,
                    "id": 1,
                    "utm_campaign": None,
                    "utm_medium": None,
                    "utm_source": "eventbrite",
                    "utm_url": None,
                    "status": "PENDING",
                    "attended_at": None,
                }
            ],
        )
        self.check_old_breathecode_calls(model, [])
        self.assertEqual(add_event_tags_to_student.delay.call_args_list, [])

    @patch("requests.get", apply_eventbrite_requests_post_mock())
    @patch("requests.request", apply_old_breathecode_requests_request_mock())
    @patch("breathecode.marketing.tasks.add_event_tags_to_student", MagicMock())
    @patch("time.sleep", MagicMock())
    def test_eventbrite_webhook_without_automation(self):
        from breathecode.marketing.tasks import add_event_tags_to_student

        model = self.generate_models(
            organization=True, event=True, event_kwargs={"eventbrite_id": 1}, active_campaign_academy=True, academy=True
        )
        url = reverse_lazy("events:eventbrite_webhook_id", kwargs={"organization_id": 1})
        response = self.client.post(
            url, self.data("order.placed", EVENTBRITE_ORDER_URL), headers=self.headers("order.placed"), format="json"
        )
        content = response.content

        self.assertEqual(content, b"ok")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        db = self.bc.database.list_of("events.EventbriteWebhook")
        self.assertRegex(db[0]["status_text"], r"Exception: Automation for order_placed doesn\'t exist\n")
        self.bc.check.partial_equality(
            db,
            [
                {
                    "action": "order.placed",
                    "api_url": "https://www.eventbriteapi.com/v3/events/1/orders/1/",
                    "endpoint_url": "https://something.io/eventbrite/webhook",
                    "id": 1,
                    "organization_id": "1",
                    "status": "ERROR",
                    "user_id": "123456789012",
                    "webhook_id": "1234567",
                }
            ],
        )

        self.assertEqual(
            self.all_event_checkin_dict(),
            [
                {
                    "attendee_id": None,
                    "email": "john.smith@example.com",
                    "utm_campaign": None,
                    "utm_medium": None,
                    "utm_source": "eventbrite",
                    "utm_url": None,
                    "event_id": 1,
                    "id": 1,
                    "status": "PENDING",
                    "attended_at": None,
                }
            ],
        )
        self.check_old_breathecode_calls(model, [])
        self.assertEqual(add_event_tags_to_student.delay.call_args_list, [])

    @patch("requests.get", apply_eventbrite_requests_post_mock())
    @patch("requests.request", apply_old_breathecode_requests_request_mock())
    @patch("breathecode.marketing.tasks.add_event_tags_to_student", MagicMock())
    @patch("time.sleep", MagicMock())
    def test_eventbrite_webhook_without_lang(self):
        from breathecode.marketing.tasks import add_event_tags_to_student

        model = self.generate_models(
            organization=True,
            event=True,
            event_kwargs={"eventbrite_id": 1},
            active_campaign_academy=True,
            automation=True,
            user=True,
            academy=True,
            active_campaign_academy_kwargs={"ac_url": "https://old.hardcoded.breathecode.url"},
            user_kwargs={"email": "john.smith@example.com", "first_name": "John", "last_name": "Smith"},
        )
        url = reverse_lazy("events:eventbrite_webhook_id", kwargs={"organization_id": 1})
        response = self.client.post(
            url, self.data("order.placed", EVENTBRITE_ORDER_URL), headers=self.headers("order.placed"), format="json"
        )
        content = response.content

        self.assertEqual(content, b"ok")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        webhook_dicts = self.all_eventbrite_webhook_dict()
        for wd in webhook_dicts:
            del wd["payload"]
        self.assertEqual(
            webhook_dicts,
            [
                {
                    "action": "order.placed",
                    "api_url": "https://www.eventbriteapi.com/v3/events/1/orders/1/",
                    "endpoint_url": "https://something.io/eventbrite/webhook",
                    "id": 1,
                    "attendee_id": 1,
                    "event_id": 1,
                    "organization_id": "1",
                    "status": "DONE",
                    "status_text": "OK",
                    "user_id": "123456789012",
                    "webhook_id": "1234567",
                }
            ],
        )

        self.assertEqual(
            self.all_event_checkin_dict(),
            [
                {
                    "attendee_id": 1,
                    "utm_campaign": None,
                    "utm_medium": None,
                    "utm_source": "eventbrite",
                    "utm_url": None,
                    "email": "john.smith@example.com",
                    "event_id": 1,
                    "id": 1,
                    "status": "PENDING",
                    "attended_at": None,
                }
            ],
        )

        self.assertEqual(
            requests.get.call_args_list,
            [
                call(
                    "https://www.eventbriteapi.com/v3/events/1/orders/1/",
                    headers={"Authorization": "Bearer "},
                    timeout=5,
                ),
            ],
        )

        assert requests.request.call_args_list == [
            call(
                "POST",
                "https://old.hardcoded.breathecode.url/admin/api.php",
                params=[
                    ("api_action", "contact_sync"),
                    ("api_key", model.active_campaign_academy.ac_key),
                    ("api_output", "json"),
                ],
                data={
                    "email": model.user.email,
                    "first_name": model.user.first_name,
                    "last_name": model.user.last_name,
                    "field[18,0]": model.academy.slug,
                    "field[59,0]": "eventbrite",
                    "field[33,0]": "eventbrite order placed",
                },
                timeout=3,
            ),
            call(
                "POST",
                "https://old.hardcoded.breathecode.url/api/3/contactAutomations",
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Api-Token": model.active_campaign_academy.ac_key,
                },
                json={
                    "contactAutomation": {
                        "contact": 1,
                        "automation": model.automation.acp_id,
                    }
                },
                timeout=2,
            ),
        ]

        self.assertEqual(
            add_event_tags_to_student.delay.call_args_list,
            [
                call(model.event.id, email=model.user.email),
            ],
        )

    @patch("requests.get", apply_eventbrite_requests_post_mock())
    @patch("requests.request", apply_old_breathecode_requests_request_mock())
    @patch("breathecode.marketing.tasks.add_event_tags_to_student", MagicMock())
    @patch("time.sleep", MagicMock())
    def test_eventbrite_webhook_without_lang__active_campaign_belong_to_other_academy_than_event(self):
        from breathecode.marketing.tasks import add_event_tags_to_student

        model = self.generate_models(
            organization=True,
            event={
                "eventbrite_id": 1,
                "academy_id": 2,
            },
            academy=2,
            active_campaign_academy={"ac_url": "https://old.hardcoded.breathecode.url"},
            automation=True,
            user={"email": "john.smith@example.com", "first_name": "John", "last_name": "Smith"},
        )
        url = reverse_lazy("events:eventbrite_webhook_id", kwargs={"organization_id": 1})
        response = self.client.post(
            url, self.data("order.placed", EVENTBRITE_ORDER_URL), headers=self.headers("order.placed"), format="json"
        )
        content = response.content

        self.assertEqual(content, b"ok")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        webhook_dict = self.all_eventbrite_webhook_dict()
        for wd in webhook_dict:
            del wd["payload"]

        self.assertEqual(
            webhook_dict,
            [
                {
                    "action": "order.placed",
                    "api_url": "https://www.eventbriteapi.com/v3/events/1/orders/1/",
                    "endpoint_url": "https://something.io/eventbrite/webhook",
                    "id": 1,
                    "attendee_id": 1,
                    "event_id": 1,
                    "organization_id": "1",
                    "status": "DONE",
                    "status_text": "OK",
                    "user_id": "123456789012",
                    "webhook_id": "1234567",
                }
            ],
        )

        self.assertEqual(
            self.all_event_checkin_dict(),
            [
                {
                    "attendee_id": 1,
                    "utm_campaign": None,
                    "utm_medium": None,
                    "utm_source": "eventbrite",
                    "utm_url": None,
                    "email": "john.smith@example.com",
                    "event_id": 1,
                    "id": 1,
                    "status": "PENDING",
                    "attended_at": None,
                }
            ],
        )

        self.assertEqual(
            requests.get.call_args_list,
            [
                call(
                    "https://www.eventbriteapi.com/v3/events/1/orders/1/",
                    headers={"Authorization": "Bearer "},
                    timeout=5,
                ),
            ],
        )

        self.assertEqual(
            requests.request.call_args_list,
            [
                call(
                    "POST",
                    "https://old.hardcoded.breathecode.url/admin/api.php",
                    params=[
                        ("api_action", "contact_sync"),
                        ("api_key", model.active_campaign_academy.ac_key),
                        ("api_output", "json"),
                    ],
                    data={
                        "email": model.user.email,
                        "first_name": model.user.first_name,
                        "last_name": model.user.last_name,
                        "field[18,0]": model.academy[1].slug,
                        "field[59,0]": "eventbrite",
                        "field[33,0]": "eventbrite order placed",
                    },
                    timeout=3,
                ),
                call(
                    "POST",
                    "https://old.hardcoded.breathecode.url/api/3/contactAutomations",
                    headers={
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                        "Api-Token": model.active_campaign_academy.ac_key,
                    },
                    json={
                        "contactAutomation": {
                            "contact": 1,
                            "automation": model.automation.acp_id,
                        }
                    },
                    timeout=2,
                ),
            ],
        )
        self.assertEqual(
            add_event_tags_to_student.delay.call_args_list,
            [
                call(model.event.id, email=model.user.email),
            ],
        )

    @patch("requests.get", apply_eventbrite_requests_post_mock())
    @patch("requests.request", apply_old_breathecode_requests_request_mock())
    @patch("breathecode.marketing.tasks.add_event_tags_to_student", MagicMock())
    @patch("time.sleep", MagicMock())
    def test_eventbrite_webhook(self):
        from breathecode.marketing.tasks import add_event_tags_to_student

        model = self.generate_models(
            organization=True,
            event=True,
            event_kwargs={"eventbrite_id": 1, "lang": "en"},
            active_campaign_academy=True,
            automation=True,
            user=True,
            academy=True,
            active_campaign_academy_kwargs={"ac_url": "https://old.hardcoded.breathecode.url"},
            user_kwargs={"email": "john.smith@example.com", "first_name": "John", "last_name": "Smith"},
        )
        url = reverse_lazy("events:eventbrite_webhook_id", kwargs={"organization_id": 1})
        response = self.client.post(
            url, self.data("order.placed", EVENTBRITE_ORDER_URL), headers=self.headers("order.placed"), format="json"
        )
        content = response.content

        self.assertEqual(content, b"ok")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        webhook_dicts = self.all_eventbrite_webhook_dict()
        for wd in webhook_dicts:
            del wd["payload"]
        self.assertEqual(
            webhook_dicts,
            [
                {
                    "action": "order.placed",
                    "api_url": "https://www.eventbriteapi.com/v3/events/1/orders/1/",
                    "endpoint_url": "https://something.io/eventbrite/webhook",
                    "id": 1,
                    "organization_id": "1",
                    "status": "DONE",
                    "event_id": 1,
                    "attendee_id": 1,
                    "status_text": "OK",
                    "user_id": "123456789012",
                    "webhook_id": "1234567",
                }
            ],
        )

        self.assertEqual(
            self.all_event_checkin_dict(),
            [
                {
                    "attendee_id": 1,
                    "utm_campaign": None,
                    "utm_medium": None,
                    "utm_source": "eventbrite",
                    "utm_url": None,
                    "email": "john.smith@example.com",
                    "event_id": 1,
                    "id": 1,
                    "status": "PENDING",
                    "attended_at": None,
                }
            ],
        )

        self.assertEqual(
            requests.get.call_args_list,
            [
                call(
                    "https://www.eventbriteapi.com/v3/events/1/orders/1/",
                    headers={"Authorization": "Bearer "},
                    timeout=5,
                ),
            ],
        )

        assert requests.request.call_args_list == [
            call(
                "POST",
                "https://old.hardcoded.breathecode.url/admin/api.php",
                params=[
                    ("api_action", "contact_sync"),
                    ("api_key", model.active_campaign_academy.ac_key),
                    ("api_output", "json"),
                ],
                data={
                    "email": model.user.email,
                    "first_name": model.user.first_name,
                    "last_name": model.user.last_name,
                    "field[18,0]": model.academy.slug,
                    "field[59,0]": "eventbrite",
                    "field[33,0]": "eventbrite order placed",
                    "field[16,0]": "en",
                },
                timeout=3,
            ),
            call(
                "POST",
                "https://old.hardcoded.breathecode.url/api/3/contactAutomations",
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Api-Token": model.active_campaign_academy.ac_key,
                },
                json={
                    "contactAutomation": {
                        "contact": 1,
                        "automation": model.automation.acp_id,
                    }
                },
                timeout=2,
            ),
        ]

        self.assertEqual(
            add_event_tags_to_student.delay.call_args_list,
            [
                call(model.event.id, email=model.user.email),
            ],
        )

    """
    🔽🔽🔽 event.created
    """

    @patch(REQUESTS_PATH["get"], apply_requests_get_mock([(200, eventbrite_url_with_query, EVENTBRITE_EVENT)]))
    @patch.object(actions, "update_or_create_event", MagicMock(side_effect=Exception("Random error in creating")))
    @patch("time.sleep", MagicMock())
    def test_eventbrite_webhook__event_created__raise_error(self):
        """Test /eventbrite/webhook without auth"""
        model = self.generate_models(organization=True)

        url = reverse_lazy("events:eventbrite_webhook_id", kwargs={"organization_id": 1})
        response = self.client.post(
            url, self.data("event.created", eventbrite_url), headers=self.headers("event.created"), format="json"
        )
        content = response.content

        self.assertEqual(content, b"ok")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(actions.update_or_create_event.call_args_list, [call(EVENTBRITE_EVENT, model.organization)])

        db = self.bc.database.list_of("events.EventbriteWebhook")
        self.assertRegex(db[0]["status_text"], r"Exception: Random error in creating\n")

        self.bc.check.partial_equality(
            db,
            [
                {
                    "action": "event.created",
                    "api_url": "https://www.eventbriteapi.com/v3/events/1/",
                    "endpoint_url": "https://something.io/eventbrite/webhook",
                    "id": 1,
                    "organization_id": "1",
                    "status": "ERROR",
                    "user_id": "123456789012",
                    "webhook_id": "1234567",
                }
            ],
        )

    @patch(REQUESTS_PATH["get"], apply_requests_get_mock([(200, eventbrite_url_with_query, EVENTBRITE_EVENT)]))
    @patch.object(actions, "update_or_create_event", update_or_create_event_mock())
    @patch("time.sleep", MagicMock())
    def test_eventbrite_webhook__event_created(self):
        """Test /eventbrite/webhook without auth"""
        model = self.generate_models(organization=True)

        url = reverse_lazy("events:eventbrite_webhook_id", kwargs={"organization_id": 1})
        response = self.client.post(
            url, self.data("event.created", eventbrite_url), headers=self.headers("event.created"), format="json"
        )
        content = response.content

        self.assertEqual(content, b"ok")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(actions.update_or_create_event.call_args_list, [call(EVENTBRITE_EVENT, model.organization)])

        webhook_dicts = self.all_eventbrite_webhook_dict()
        for wd in webhook_dicts:
            del wd["payload"]
        self.assertEqual(
            webhook_dicts,
            [
                {
                    "action": "event.created",
                    "api_url": "https://www.eventbriteapi.com/v3/events/1/",
                    "endpoint_url": "https://something.io/eventbrite/webhook",
                    "id": 1,
                    "organization_id": "1",
                    "attendee_id": None,
                    "event_id": None,
                    "status": "DONE",
                    "status_text": "OK",
                    "user_id": "123456789012",
                    "webhook_id": "1234567",
                }
            ],
        )

    """
    🔽🔽🔽 event.updated
    """

    @patch(REQUESTS_PATH["get"], apply_requests_get_mock([(200, eventbrite_url_with_query, EVENTBRITE_EVENT)]))
    @patch.object(actions, "update_or_create_event", MagicMock(side_effect=Exception("Random error in creating")))
    @patch("time.sleep", MagicMock())
    def test_eventbrite_webhook__event_updated__raise_error(self):
        """Test /eventbrite/webhook without auth"""
        model = self.generate_models(organization=True)

        url = reverse_lazy("events:eventbrite_webhook_id", kwargs={"organization_id": 1})
        response = self.client.post(
            url, self.data("event.updated", eventbrite_url), headers=self.headers("event.updated"), format="json"
        )
        content = response.content

        self.assertEqual(content, b"ok")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(actions.update_or_create_event.call_args_list, [call(EVENTBRITE_EVENT, model.organization)])

        db = self.bc.database.list_of("events.EventbriteWebhook")
        self.assertRegex(db[0]["status_text"], r"Exception: Random error in creating\n")

        self.bc.check.partial_equality(
            db,
            [
                {
                    "action": "event.updated",
                    "api_url": "https://www.eventbriteapi.com/v3/events/1/",
                    "endpoint_url": "https://something.io/eventbrite/webhook",
                    "id": 1,
                    "organization_id": "1",
                    "status": "ERROR",
                    "user_id": "123456789012",
                    "webhook_id": "1234567",
                }
            ],
        )

    @patch(REQUESTS_PATH["get"], apply_requests_get_mock([(200, eventbrite_url_with_query, EVENTBRITE_EVENT)]))
    @patch.object(actions, "update_or_create_event", update_or_create_event_mock())
    @patch("time.sleep", MagicMock())
    def test_eventbrite_webhook__event_updated(self):
        """Test /eventbrite/webhook without auth"""
        model = self.generate_models(organization=True)

        url = reverse_lazy("events:eventbrite_webhook_id", kwargs={"organization_id": 1})
        response = self.client.post(
            url, self.data("event.updated", eventbrite_url), headers=self.headers("event.updated"), format="json"
        )
        content = response.content

        self.assertEqual(content, b"ok")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(actions.update_or_create_event.call_args_list, [call(EVENTBRITE_EVENT, model.organization)])

        webhook_dicts = self.all_eventbrite_webhook_dict()
        for wd in webhook_dicts:
            del wd["payload"]
        self.assertEqual(
            webhook_dicts,
            [
                {
                    "action": "event.updated",
                    "api_url": "https://www.eventbriteapi.com/v3/events/1/",
                    "endpoint_url": "https://something.io/eventbrite/webhook",
                    "id": 1,
                    "attendee_id": None,
                    "event_id": None,
                    "organization_id": "1",
                    "status": "DONE",
                    "status_text": "OK",
                    "user_id": "123456789012",
                    "webhook_id": "1234567",
                }
            ],
        )

    """
    🔽🔽🔽 event.published
    """

    @patch(REQUESTS_PATH["get"], apply_requests_get_mock([(200, eventbrite_url_with_query, EVENTBRITE_EVENT)]))
    @patch("breathecode.events.actions.publish_event_from_eventbrite", MagicMock(side_effect=Exception("Random error")))
    @patch("time.sleep", MagicMock())
    def test_eventbrite_webhook__event_published__raise_error(self):
        from breathecode.events.actions import publish_event_from_eventbrite

        model = self.generate_models(organization=True)

        url = reverse_lazy("events:eventbrite_webhook_id", kwargs={"organization_id": 1})
        response = self.client.post(
            url, self.data("event.published", eventbrite_url), headers=self.headers("event.published"), format="json"
        )
        content = response.content

        self.assertEqual(content, b"ok")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(publish_event_from_eventbrite.call_args_list, [call(EVENTBRITE_EVENT, model.organization)])

        db = self.bc.database.list_of("events.EventbriteWebhook")
        self.assertRegex(db[0]["status_text"], r"Exception: Random error\n")

        self.bc.check.partial_equality(
            db,
            [
                {
                    "action": "event.published",
                    "api_url": "https://www.eventbriteapi.com/v3/events/1/",
                    "endpoint_url": "https://something.io/eventbrite/webhook",
                    "id": 1,
                    "organization_id": "1",
                    "status": "ERROR",
                    "user_id": "123456789012",
                    "webhook_id": "1234567",
                }
            ],
        )

    @patch(REQUESTS_PATH["get"], apply_requests_get_mock([(200, eventbrite_url_with_query, EVENTBRITE_EVENT)]))
    @patch.object(actions, "publish_event_from_eventbrite", MagicMock(return_value=None))
    @patch("time.sleep", MagicMock())
    def test_eventbrite_webhook__event_published(self):
        from breathecode.events.actions import publish_event_from_eventbrite

        model = self.generate_models(organization=True)

        url = reverse_lazy("events:eventbrite_webhook_id", kwargs={"organization_id": 1})
        response = self.client.post(
            url, self.data("event.published", eventbrite_url), headers=self.headers("event.published"), format="json"
        )
        content = response.content

        self.assertEqual(content, b"ok")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        webhook_dicts = self.all_eventbrite_webhook_dict()
        for wd in webhook_dicts:
            del wd["payload"]
        self.assertEqual(
            webhook_dicts,
            [
                {
                    "action": "event.published",
                    "api_url": "https://www.eventbriteapi.com/v3/events/1/",
                    "endpoint_url": "https://something.io/eventbrite/webhook",
                    "id": 1,
                    "attendee_id": None,
                    "event_id": None,
                    "organization_id": "1",
                    "status": "DONE",
                    "status_text": "OK",
                    "user_id": "123456789012",
                    "webhook_id": "1234567",
                }
            ],
        )
