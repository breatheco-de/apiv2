import logging
import breathecode.events.actions as actions
from unittest.mock import MagicMock, call, patch
from django.utils import timezone
from breathecode.tests.mocks.requests import REQUESTS_PATH, apply_requests_request_mock
from ..mixins import EventTestCase

update_event_description_from_eventbrite = actions.update_event_description_from_eventbrite
sync_desc = "2021-11-23 09:10:58.295264+00:00"
eventbrite_get_url = "https://www.eventbriteapi.com/v3/events/1/structured_content/"
eventbrite_post_url = "https://www.eventbriteapi.com/v3/events/1/structured_content/1/"
eventbrite_bad_get_event = {}
eventbrite_good_get_event = {"modules": [{"data": {"body": {"text": "They Killed Kenny"}}}]}
status_map = {
    "draft": "DRAFT",
    "live": "ACTIVE",
    "completed": "COMPLETED",
    "started": "ACTIVE",
    "ended": "ACTIVE",
    "canceled": "DELETED",
}

UTC_NOW = timezone.now()


class SyncOrgVenuesTestSuite(EventTestCase):
    """
    🔽🔽🔽 Without Event
    """

    @patch.object(logging.Logger, "warning", MagicMock())
    @patch.object(logging.Logger, "error", MagicMock())
    @patch.object(timezone, "now", MagicMock(return_value=UTC_NOW))
    @patch(REQUESTS_PATH["request"], apply_requests_request_mock([(200, eventbrite_get_url, eventbrite_bad_get_event)]))
    def test_update_event_description_from_eventbrite__without_event(self):
        import logging
        import requests

        update_event_description_from_eventbrite(None)

        self.assertEqual(logging.Logger.warning.call_args_list, [])
        self.assertEqual(logging.Logger.error.call_args_list, [call("Event is not being provided")])

        self.assertEqual(self.bc.database.list_of("events.Event"), [])
        self.assertEqual(requests.request.call_args_list, [])

    """
    🔽🔽🔽 Without eventbrite id
    """

    @patch.object(logging.Logger, "warning", MagicMock())
    @patch.object(logging.Logger, "error", MagicMock())
    @patch.object(timezone, "now", MagicMock(return_value=UTC_NOW))
    @patch(REQUESTS_PATH["request"], apply_requests_request_mock([(200, eventbrite_get_url, eventbrite_bad_get_event)]))
    def test_update_event_description_from_eventbrite__without_eventbrite_id(self):
        import logging
        import requests

        model = self.generate_models(event=1)
        db = self.bc.format.to_dict(model.event)

        update_event_description_from_eventbrite(model.event)

        self.assertEqual(logging.Logger.warning.call_args_list, [])
        self.assertEqual(
            logging.Logger.error.call_args_list,
            [
                call("Event 1 not have the integration with eventbrite"),
            ],
        )

        self.assertEqual(self.bc.database.list_of("events.Event"), [db])
        self.assertEqual(requests.request.call_args_list, [])

    """
    🔽🔽🔽 With Event
    """

    @patch.object(logging.Logger, "warning", MagicMock())
    @patch.object(logging.Logger, "error", MagicMock())
    @patch.object(timezone, "now", MagicMock(return_value=UTC_NOW))
    @patch(REQUESTS_PATH["request"], apply_requests_request_mock([(200, eventbrite_get_url, eventbrite_bad_get_event)]))
    def test_update_event_description_from_eventbrite__with_event(self):
        import logging
        import requests

        event = {"eventbrite_id": "1"}
        model = self.generate_models(event=event)
        db = self.bc.format.to_dict(model.event)

        update_event_description_from_eventbrite(model.event)

        self.assertEqual(logging.Logger.warning.call_args_list, [])
        self.assertEqual(
            logging.Logger.error.call_args_list,
            [
                call("Event 1 not have a organization assigned"),
            ],
        )

        self.assertEqual(self.bc.database.list_of("events.Event"), [db])
        self.assertEqual(requests.request.call_args_list, [])

    """
    🔽🔽🔽 Without description in eventbrite
    """

    @patch.object(logging.Logger, "warning", MagicMock())
    @patch.object(logging.Logger, "error", MagicMock())
    @patch.object(timezone, "now", MagicMock(return_value=UTC_NOW))
    @patch(REQUESTS_PATH["request"], apply_requests_request_mock([(200, eventbrite_get_url, eventbrite_bad_get_event)]))
    def test_update_event_description_from_eventbrite__without_event_in_eventbrite(self):
        import logging
        import requests

        organization = {"eventbrite_id": "1", "eventbrite_key": "x"}
        event = {"eventbrite_id": "1"}
        model = self.generate_models(event=event, organization=organization)
        db = self.bc.format.to_dict(model.event)

        update_event_description_from_eventbrite(model.event)

        self.assertEqual(
            logging.Logger.warning.call_args_list,
            [
                call("The event 1 is coming from eventbrite not have a description"),
            ],
        )
        self.assertEqual(logging.Logger.error.call_args_list, [])

        self.assertEqual(self.bc.database.list_of("events.Event"), [db])
        self.assertEqual(
            requests.request.call_args_list,
            [
                call(
                    "GET",
                    "https://www.eventbriteapi.com/v3/events/1/structured_content/",
                    headers={"Authorization": f"Bearer {model.organization.eventbrite_key}"},
                    data=None,
                    timeout=2,
                )
            ],
        )

    """
    🔽🔽🔽 With description in eventbrite
    """

    @patch.object(logging.Logger, "warning", MagicMock())
    @patch.object(logging.Logger, "error", MagicMock())
    @patch.object(timezone, "now", MagicMock(return_value=UTC_NOW))
    @patch(
        REQUESTS_PATH["request"], apply_requests_request_mock([(200, eventbrite_get_url, eventbrite_good_get_event)])
    )
    def test_update_event_description_from_eventbrite__with_event_in_eventbrite(self):
        import logging
        import requests

        organization = {"eventbrite_id": "1", "eventbrite_key": "x"}
        event = {"eventbrite_id": "1"}
        model = self.generate_models(event=event, organization=organization)
        db = self.bc.format.to_dict(model.event)

        update_event_description_from_eventbrite(model.event)

        self.assertEqual(logging.Logger.warning.call_args_list, [])
        self.assertEqual(logging.Logger.error.call_args_list, [])

        self.assertEqual(
            self.bc.database.list_of("events.Event"),
            [
                {
                    **db,
                    "description": "They Killed Kenny",
                    "eventbrite_sync_status": "PERSISTED",
                    "eventbrite_sync_description": str(UTC_NOW),
                }
            ],
        )

        self.assertEqual(
            requests.request.call_args_list,
            [
                call(
                    "GET",
                    "https://www.eventbriteapi.com/v3/events/1/structured_content/",
                    headers={"Authorization": f"Bearer {model.organization.eventbrite_key}"},
                    data=None,
                    timeout=2,
                )
            ],
        )
