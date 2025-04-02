import random
import re
from unittest.mock import MagicMock, call, patch

from dateutil.relativedelta import relativedelta

from breathecode.events.models import Event
from breathecode.events.tasks import generate_event_recap
from breathecode.tests.mocks import apply_requests_get_mock, apply_requests_post_mock

from ..mixins.new_events_tests_case import EventTestCase


class GenerateEventRecapTaskTestSuite(EventTestCase):
    """Tests for generate_event_recap task"""

    @patch("logging.Logger.error")
    def test_generate_event_recap__event_not_found(self, logger_mock):
        """Test case where Event does not exist"""
        generate_event_recap.delay(event_id=999)
        logger_mock.assert_called_once_with("Event 999 not found")

    @patch("logging.Logger.info")
    def test_generate_event_recap__event_already_has_recap(self, logger_mock):
        """Test case where Event already has a recap"""
        event = self.bc.database.create(event={"recap": "Existing recap"})
        generate_event_recap.delay(event_id=event.event.id)
        logger_mock.assert_any_call(f"Event {event.event.id} already has a recap, skipping")
        event_db = self.bc.database.get("events.Event", event.event.id, dict=False)
        self.assertEqual(event_db.recap, "Existing recap")  # Recap should not change

    @patch("breathecode.events.tasks.Service")
    @patch("logging.Logger.error")
    def test_generate_event_recap__rigobot_service_exception(self, logger_mock, service_mock):
        """Test case where rigobot service call raises an exception"""
        event = self.bc.database.create(event=1)
        # Configure the mock returned by __enter__ to raise an exception on post
        service_instance_mock = MagicMock()
        service_instance_mock.post.side_effect = Exception("Rigobot Down")
        service_mock.return_value.__enter__.return_value = service_instance_mock

        generate_event_recap.delay(event_id=event.event.id)

        logger_mock.assert_called_once_with(f"Error generating recap for event {event.event.id}: Rigobot Down")
        service_mock.assert_called_once_with("rigobot", event.event.id)
        service_instance_mock.post.assert_called_once()
        event_db = self.bc.database.get("events.Event", event.event.id, dict=False)
        self.assertIsNone(event_db.recap)

    @patch("breathecode.events.tasks.Service")
    @patch("logging.Logger.error")
    def test_generate_event_recap__rigobot_api_error(self, logger_mock, service_mock):
        """Test case where rigobot API returns an error status code"""
        event = self.bc.database.create(event=1)
        # Configure the mock returned by __enter__ to return a failed response on post
        service_instance_mock = MagicMock()
        service_instance_mock.post.return_value = MagicMock(status_code=500, text="Internal Server Error")
        service_mock.return_value.__enter__.return_value = service_instance_mock

        generate_event_recap.delay(event_id=event.event.id)

        logger_mock.assert_called_once_with("Failed to generate recap: 500 - Internal Server Error")
        service_mock.assert_called_once_with("rigobot", event.event.id)
        service_instance_mock.post.assert_called_once()
        event_db = self.bc.database.get("events.Event", event.event.id, dict=False)
        self.assertIsNone(event_db.recap)

    @patch("breathecode.events.tasks.Service")
    @patch("logging.Logger.warning")
    def test_generate_event_recap__recap_not_extracted(self, logger_mock, service_mock):
        """Test case where the recap text cannot be extracted from the API response"""
        event_data = {"title": "Test Event", "description": "Event description.", "tags": ["tech"]}
        event = self.bc.database.create(event=event_data)
        api_response_json = {"answer": "Some unexpected response format"}
        # Configure the mock returned by __enter__ for the post call
        service_instance_mock = MagicMock()
        service_instance_mock.post.return_value = MagicMock(
            status_code=200, json=lambda: api_response_json, text=str(api_response_json)
        )
        service_mock.return_value.__enter__.return_value = service_instance_mock

        generate_event_recap.delay(event_id=event.event.id)

        expected_payload = {
            "inputs": {
                "event_title": event.event.title,
                "event_description": event.event.description,
                "event_type": event.event.tags[0],
            },
            "execute_async": False,
        }
        service_mock.assert_called_once_with("rigobot", event.event.id)
        service_instance_mock.post.assert_called_once_with(
            "/v1/prompting/completion/linked/event-recap/", json=expected_payload
        )
        logger_mock.assert_called_once_with(
            "Recap for event 1 could not be extracted from answer: Some unexpected response format..."
        )
        event_db = self.bc.database.get("events.Event", event.event.id, dict=False)
        self.assertIsNone(event_db.recap)

    @patch("breathecode.events.tasks.Service")
    @patch("logging.Logger.info")
    def test_generate_event_recap__success(self, logger_mock, service_mock):
        """Test successful recap generation and saving"""
        event_data = {"title": "Successful Event", "description": "Description here.", "tags": ["community"]}
        event = self.bc.database.create(event=event_data)
        recap_text = "This is the generated recap."
        api_response_json = {"answer": f"<event-description>{recap_text}</event-description>"}
        # Configure the mock returned by __enter__ for the post call
        service_instance_mock = MagicMock()
        service_instance_mock.post.return_value = MagicMock(
            status_code=200, json=lambda: api_response_json, text=str(api_response_json)
        )
        service_mock.return_value.__enter__.return_value = service_instance_mock

        generate_event_recap.delay(event_id=event.event.id)

        expected_payload = {
            "inputs": {
                "event_title": event.event.title,
                "event_description": event.event.description,
                "event_type": event.event.tags[0],
            },
            "execute_async": False,
        }
        service_mock.assert_called_once_with("rigobot", event.event.id)
        service_instance_mock.post.assert_called_once_with(
            "/v1/prompting/completion/linked/event-recap/", json=expected_payload
        )
        event_db = self.bc.database.get("events.Event", event.event.id, dict=False)
        self.assertEqual(event_db.recap, recap_text)
        logger_mock.assert_any_call(
            f"API call successful for event {event.event.id}, response: {str(api_response_json)}"
        )
