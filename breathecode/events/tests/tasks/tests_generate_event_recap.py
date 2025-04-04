from unittest.mock import MagicMock, patch

import pytest
from task_manager.core.exceptions import AbortTask, RetryTask

from breathecode.events.models import Event, EventContext
from breathecode.events.tasks import generate_event_recap

pytestmark = pytest.mark.django_db


@pytest.fixture
def event_factory(database):
    """Create an event for testing"""

    def _event_factory(recap=None, **kwargs):
        event_data = {"title": "Test Event", "description": "Event description", "tags": ["tech"]}
        event_data.update(kwargs)
        event_obj = database.create(event=event_data).event

        if recap:
            context = EventContext(event=event_obj, recap=recap)
            context.save()

        return event_obj

    return _event_factory


@patch("logging.Logger.error")
def test_event_not_found(logger_mock):
    """Test case where Event does not exist"""
    generate_event_recap(event_id=999)

    logger_mock.assert_any_call("Event 999 not found")


@patch("logging.Logger.info")
def test_event_already_has_recap(logger_mock, event_factory):
    """Test case where Event already has a recap"""
    event = event_factory(recap="Existing recap")

    generate_event_recap(event_id=event.id)

    logger_mock.assert_any_call(f"Event {event.id} already has a recap, skipping")
    context = EventContext.objects.get(event=event)
    assert context.recap == "Existing recap"  # Recap should not change


@patch("breathecode.events.tasks.Service")
def test_rigobot_service_exception(service_mock, event_factory):
    """Test case where rigobot service call raises an exception"""
    event = event_factory()

    service_instance_mock = MagicMock()
    service_instance_mock.post.side_effect = Exception("Rigobot Down")
    service_mock.return_value.__enter__.return_value = service_instance_mock

    generate_event_recap(event_id=event.id)

    service_mock.assert_any_call("rigobot", event.id)

    context = EventContext.objects.get(event=event)
    assert context.status == EventContext.Status.ERROR
    assert "Rigobot Down" in context.status_text


@patch("breathecode.events.tasks.Service")
def test_rigobot_api_error(service_mock, event_factory):
    """Test case where rigobot API returns an error status code"""
    event = event_factory()

    service_instance_mock = MagicMock()
    service_instance_mock.post.return_value = MagicMock(status_code=500, text="Internal Server Error")
    service_mock.return_value.__enter__.return_value = service_instance_mock

    generate_event_recap(event_id=event.id)

    service_mock.assert_any_call("rigobot", event.id)

    context = EventContext.objects.get(event=event)
    assert context.status == EventContext.Status.ERROR
    assert "Failed to generate recap: 500" in context.status_text


@patch("breathecode.events.tasks.Service")
def test_recap_not_extracted(service_mock, event_factory):
    """Test case where the recap text cannot be extracted from the API response"""
    event = event_factory()

    api_response_json = {"answer": "Some unexpected response format"}
    service_instance_mock = MagicMock()
    service_instance_mock.post.return_value = MagicMock(
        status_code=200, json=lambda: api_response_json, text=str(api_response_json)
    )
    service_mock.return_value.__enter__.return_value = service_instance_mock

    generate_event_recap(event_id=event.id)

    service_mock.assert_any_call("rigobot", event.id)

    context = EventContext.objects.get(event=event)
    assert context.status == EventContext.Status.ERROR
    assert "Recap text could not be extracted" in context.status_text


@patch("breathecode.events.tasks.Service")
@patch("logging.Logger.info")
def test_generate_event_recap_success(logger_mock, service_mock, event_factory):
    """Test successful recap generation and saving"""
    event = event_factory(title="Successful Event", description="Description here.", tags=["community"])

    recap_text = "This is the generated recap."
    api_response_json = {"answer": f"<event-description>{recap_text}</event-description>"}

    service_instance_mock = MagicMock()
    service_instance_mock.post.return_value = MagicMock(
        status_code=200, json=lambda: api_response_json, text=str(api_response_json)
    )
    service_mock.return_value.__enter__.return_value = service_instance_mock

    generate_event_recap(event_id=event.id)

    service_mock.assert_any_call("rigobot", event.id)

    context = EventContext.objects.get(event=event)
    assert context.recap == recap_text
    assert context.status == EventContext.Status.SUCCESS

    assert any("API call successful" in str(call) and str(event.id) in str(call) for call in logger_mock.call_args_list)
