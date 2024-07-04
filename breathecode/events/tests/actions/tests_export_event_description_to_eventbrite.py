import logging
import breathecode.events.actions as actions
from unittest.mock import MagicMock, call, patch
from django.utils import timezone

from breathecode.tests.mocks.requests import REQUESTS_PATH, apply_requests_request_mock
from ..mixins import EventTestCase

export_event_description_to_eventbrite = actions.export_event_description_to_eventbrite
sync_desc = "2021-11-23 09:10:58.295264+00:00"
eventbrite_get_url = "https://www.eventbriteapi.com/v3/events/1/structured_content/"
eventbrite_post_url = "https://www.eventbriteapi.com/v3/events/1/structured_content/1/"
eventbrite_get_event = {"page_version_number": "1"}
eventbrite_good_post_event = {"modules": [{"id": "1"}]}
eventbrite_bad_post_event = {"modules": []}
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
    @patch(
        REQUESTS_PATH["request"],
        apply_requests_request_mock(
            [
                (400, eventbrite_post_url, eventbrite_bad_post_event),
                (200, eventbrite_get_url, eventbrite_get_event),
            ]
        ),
    )
    def test_export_event_description_to_eventbrite__without_event(self):
        import logging
        import requests

        export_event_description_to_eventbrite(None)

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
    @patch(
        REQUESTS_PATH["request"],
        apply_requests_request_mock(
            [
                (400, eventbrite_post_url, eventbrite_bad_post_event),
                (200, eventbrite_get_url, eventbrite_get_event),
            ]
        ),
    )
    def test_export_event_description_to_eventbrite__without_eventbrite_id(self):
        import logging
        import requests

        model = self.generate_models(event=1)
        db = self.bc.format.to_dict(model.event)

        export_event_description_to_eventbrite(model.event)

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
    @patch(
        REQUESTS_PATH["request"],
        apply_requests_request_mock(
            [
                (400, eventbrite_post_url, eventbrite_bad_post_event),
                (200, eventbrite_get_url, eventbrite_get_event),
            ]
        ),
    )
    def test_export_event_description_to_eventbrite__with_event(self):
        import logging
        import requests

        event = {"eventbrite_id": "1"}
        model = self.generate_models(event=event)
        db = self.bc.format.to_dict(model.event)

        export_event_description_to_eventbrite(model.event)

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
    🔽🔽🔽 Empty description
    """

    @patch.object(logging.Logger, "warning", MagicMock())
    @patch.object(logging.Logger, "error", MagicMock())
    @patch.object(timezone, "now", MagicMock(return_value=UTC_NOW))
    @patch(
        REQUESTS_PATH["request"],
        apply_requests_request_mock(
            [
                (400, eventbrite_post_url, eventbrite_bad_post_event),
                (200, eventbrite_get_url, eventbrite_get_event),
            ]
        ),
    )
    def test_export_event_description_to_eventbrite__empty_description(self):
        import logging
        import requests

        organization = {"eventbrite_id": "1", "eventbrite_key": "x"}
        event = {"eventbrite_id": "1", "description": ""}
        model = self.generate_models(event=event, organization=organization)
        db = self.bc.format.to_dict(model.event)

        export_event_description_to_eventbrite(model.event)

        self.assertEqual(
            logging.Logger.warning.call_args_list,
            [
                call("The event 1 not have description yet"),
            ],
        )
        self.assertEqual(logging.Logger.error.call_args_list, [])

        self.assertEqual(self.bc.database.list_of("events.Event"), [db])
        self.assertEqual(requests.request.call_args_list, [])

    """
    🔽🔽🔽 The eventbrite response is changed and now emit a exception
    """

    @patch.object(logging.Logger, "warning", MagicMock())
    @patch.object(logging.Logger, "error", MagicMock())
    @patch.object(timezone, "now", MagicMock(return_value=UTC_NOW))
    @patch(
        REQUESTS_PATH["request"],
        apply_requests_request_mock(
            [
                (400, eventbrite_post_url, eventbrite_bad_post_event),
                (200, eventbrite_get_url, {}),
            ]
        ),
    )
    def test_export_event_description_to_eventbrite__the_get_not_return_page_version_number(self):
        import logging
        import requests

        organization = {"eventbrite_id": "1", "eventbrite_key": "x"}
        event = {"eventbrite_id": "1", "description": "The killed kenny"}
        model = self.generate_models(event=event, organization=organization)
        db = self.bc.format.to_dict(model.event)

        export_event_description_to_eventbrite(model.event)

        self.assertEqual(logging.Logger.warning.call_args_list, [])
        self.assertEqual(
            logging.Logger.error.call_args_list,
            [
                call("'page_version_number'"),
            ],
        )

        self.assertEqual(
            self.bc.database.list_of("events.Event"),
            [
                {
                    **db,
                    "eventbrite_sync_description": "'page_version_number'",
                    "eventbrite_sync_status": "ERROR",
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

    """
    🔽🔽🔽 The description could not be saved
    """

    @patch.object(logging.Logger, "warning", MagicMock())
    @patch.object(logging.Logger, "error", MagicMock())
    @patch.object(timezone, "now", MagicMock(return_value=UTC_NOW))
    @patch(
        REQUESTS_PATH["request"],
        apply_requests_request_mock(
            [
                (400, eventbrite_post_url, eventbrite_bad_post_event),
                (200, eventbrite_get_url, eventbrite_get_event),
            ]
        ),
    )
    def test_export_event_description_to_eventbrite__post_with_400(self):
        import logging
        import requests

        organization = {"eventbrite_id": "1", "eventbrite_key": "x"}
        event = {"eventbrite_id": "1", "description": "The killed kenny"}
        model = self.generate_models(event=event, organization=organization)
        db = self.bc.format.to_dict(model.event)

        export_event_description_to_eventbrite(model.event)

        self.assertEqual(logging.Logger.warning.call_args_list, [])
        self.assertEqual(
            logging.Logger.error.call_args_list,
            [
                call("Could not create event description in eventbrite"),
            ],
        )

        self.assertEqual(
            self.bc.database.list_of("events.Event"),
            [
                {
                    **db,
                    "eventbrite_sync_status": "ERROR",
                    "eventbrite_sync_description": "Could not create event description in eventbrite",
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
                ),
                call(
                    "POST",
                    "https://www.eventbriteapi.com/v3/events/1/structured_content/1/",
                    headers={"Authorization": f"Bearer {model.organization.eventbrite_key}"},
                    data={
                        "modules": [
                            {
                                "type": "text",
                                "data": {"body": {"type": "text", "text": "The killed kenny", "alignment": "left"}},
                            }
                        ],
                        "publish": True,
                        "purpose": "listing",
                    },
                    timeout=2,
                ),
            ],
        )

    """
    🔽🔽🔽 The description was saved
    """

    @patch.object(logging.Logger, "warning", MagicMock())
    @patch.object(logging.Logger, "error", MagicMock())
    @patch.object(timezone, "now", MagicMock(return_value=UTC_NOW))
    @patch(
        REQUESTS_PATH["request"],
        apply_requests_request_mock(
            [
                (200, eventbrite_post_url, eventbrite_good_post_event),
                (200, eventbrite_get_url, eventbrite_get_event),
            ]
        ),
    )
    def test_export_event_description_to_eventbrite(self):
        import logging
        import requests

        organization = {"eventbrite_id": "1", "eventbrite_key": "x"}
        event = {"eventbrite_id": "1", "description": "The killed kenny"}
        model = self.generate_models(event=event, organization=organization)
        db = self.bc.format.to_dict(model.event)

        export_event_description_to_eventbrite(model.event)

        self.assertEqual(logging.Logger.warning.call_args_list, [])
        self.assertEqual(logging.Logger.error.call_args_list, [])

        self.assertEqual(
            self.bc.database.list_of("events.Event"),
            [
                {
                    **db,
                    "eventbrite_sync_status": "SYNCHED",
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
                ),
                call(
                    "POST",
                    "https://www.eventbriteapi.com/v3/events/1/structured_content/1/",
                    headers={"Authorization": f"Bearer {model.organization.eventbrite_key}"},
                    data={
                        "modules": [
                            {
                                "type": "text",
                                "data": {"body": {"type": "text", "text": "The killed kenny", "alignment": "left"}},
                            }
                        ],
                        "publish": True,
                        "purpose": "listing",
                    },
                    timeout=2,
                ),
            ],
        )
