import logging

from datetime import datetime
from unittest.mock import MagicMock, call, patch

from breathecode.tests.mocks import REQUESTS_PATH, apply_requests_request_mock
from breathecode.tests.mocks.eventbrite.constants.events import EVENTBRITE_EVENTS, get_eventbrite_events_url
from ..mixins import EventTestCase
import breathecode.events.actions as actions

sync_org_events = actions.sync_org_events

eventbrite_events_endpoint = get_eventbrite_events_url("1")


def log_mock():

    def log(self, *args):
        print(*args)

    return MagicMock(side_effect=log)


def update_or_create_event_mock(raise_error=False):

    def update_or_create_event(self, *args, **kwargs):
        if raise_error:
            raise Exception("Random error in creating")

    return MagicMock(side_effect=update_or_create_event)


def export_event_to_eventbrite_mock(raise_error=False):

    def export_event_to_eventbrite(self, *args, **kwargs):
        if raise_error:
            raise Exception("Random error getting")

    return MagicMock(side_effect=export_event_to_eventbrite)


class SyncOrgVenuesTestSuite(EventTestCase):
    """
    🔽🔽🔽 Without academy
    """

    @patch.object(logging.Logger, "info", log_mock())
    @patch.object(logging.Logger, "error", log_mock())
    @patch.object(actions, "update_or_create_event", update_or_create_event_mock())
    @patch.object(actions, "export_event_to_eventbrite", export_event_to_eventbrite_mock())
    @patch(
        REQUESTS_PATH["request"], apply_requests_request_mock([(200, eventbrite_events_endpoint, EVENTBRITE_EVENTS)])
    )
    def test_sync_org_events__without_academy(self):
        """Test /answer without auth"""
        import logging
        import breathecode.events.actions as actions

        organization_kwargs = {"eventbrite_id": "1"}
        model = self.generate_models(organization=True, organization_kwargs=organization_kwargs)
        logging.Logger.info.call_args_list = []

        sync_org_events(model["organization"])

        self.assertEqual(actions.export_event_to_eventbrite.call_args_list, [])
        self.assertEqual(actions.update_or_create_event.call_args_list, [])
        self.assertEqual(logging.Logger.info.call_args_list, [])
        self.assertEqual(
            logging.Logger.error.call_args_list, [call("The organization Nameless not have a academy assigned")]
        )

        self.assertEqual(self.all_organization_dict(), [self.model_to_dict(model, "organization")])
        self.assertEqual(self.bc.database.list_of("events.Event"), [])

    """
    🔽🔽🔽 With academy, call update_or_create_event
    """

    @patch.object(logging.Logger, "info", log_mock())
    @patch.object(logging.Logger, "error", log_mock())
    @patch.object(actions, "update_or_create_event", update_or_create_event_mock())
    @patch.object(actions, "export_event_to_eventbrite", export_event_to_eventbrite_mock())
    @patch(
        REQUESTS_PATH["request"], apply_requests_request_mock([(200, eventbrite_events_endpoint, EVENTBRITE_EVENTS)])
    )
    def test_sync_org_events(self):
        """Test /answer without auth"""
        import logging
        import breathecode.events.actions as actions

        organization_kwargs = {"eventbrite_id": "1"}
        model = self.generate_models(academy=True, organization=True, organization_kwargs=organization_kwargs)
        logging.Logger.info.call_args_list = []

        sync_org_events(model["organization"])

        self.assertEqual(actions.export_event_to_eventbrite.call_args_list, [])
        self.assertEqual(
            actions.update_or_create_event.call_args_list, [call(EVENTBRITE_EVENTS["events"][0], model.organization)]
        )

        self.assertEqual(logging.Logger.info.call_args_list, [])
        self.assertEqual(logging.Logger.error.call_args_list, [])

        self.assertEqual(self.all_organization_dict(), [self.model_to_dict(model, "organization")])
        self.assertEqual(self.bc.database.list_of("events.Event"), [])

    """
    🔽🔽🔽 With academy, raise error
    """

    @patch.object(logging.Logger, "info", log_mock())
    @patch.object(logging.Logger, "error", log_mock())
    @patch.object(actions, "update_or_create_event", update_or_create_event_mock(raise_error=True))
    @patch.object(actions, "export_event_to_eventbrite", export_event_to_eventbrite_mock())
    @patch(
        REQUESTS_PATH["request"], apply_requests_request_mock([(200, eventbrite_events_endpoint, EVENTBRITE_EVENTS)])
    )
    def test_sync_org_events__raise_error(self):
        """Test /answer without auth"""
        import logging
        import breathecode.events.actions as actions

        organization_kwargs = {"eventbrite_id": "1"}
        model = self.generate_models(academy=True, organization=True, organization_kwargs=organization_kwargs)
        logging.Logger.info.call_args_list = []

        with self.assertRaises(Exception) as cm:
            sync_org_events(model["organization"])

        self.assertEqual(str(cm.exception), "Random error in creating")
        self.assertEqual(actions.export_event_to_eventbrite.call_args_list, [])
        self.assertEqual(
            actions.update_or_create_event.call_args_list, [call(EVENTBRITE_EVENTS["events"][0], model.organization)]
        )

        self.assertEqual(logging.Logger.info.call_args_list, [])
        self.assertEqual(logging.Logger.error.call_args_list, [])

        self.assertEqual(
            self.all_organization_dict(),
            [
                {
                    **self.model_to_dict(model, "organization"),
                    "sync_status": "ERROR",
                    "sync_desc": "Error: Random error in creating",
                }
            ],
        )

        self.assertEqual(self.bc.database.list_of("events.Event"), [])

    """
    🔽🔽🔽 With academy, call export_event_to_eventbrite, without events
    """

    @patch.object(logging.Logger, "info", log_mock())
    @patch.object(logging.Logger, "error", log_mock())
    @patch.object(actions, "update_or_create_event", update_or_create_event_mock())
    @patch.object(actions, "export_event_to_eventbrite", export_event_to_eventbrite_mock())
    @patch(
        REQUESTS_PATH["request"], apply_requests_request_mock([(200, eventbrite_events_endpoint, EVENTBRITE_EVENTS)])
    )
    def test_sync_org_events__call_export_event_to_eventbrite__without_events(self):
        """Test /answer without auth"""
        import logging
        import breathecode.events.actions as actions

        organization_kwargs = {"eventbrite_id": "1"}
        model = self.generate_models(academy=True, organization=True, organization_kwargs=organization_kwargs)
        logging.Logger.info.call_args_list = []

        sync_org_events(model["organization"])

        self.assertEqual(actions.export_event_to_eventbrite.call_args_list, [])
        self.assertEqual(
            actions.update_or_create_event.call_args_list, [call(EVENTBRITE_EVENTS["events"][0], model.organization)]
        )

        self.assertEqual(logging.Logger.info.call_args_list, [])
        self.assertEqual(logging.Logger.error.call_args_list, [])

        self.assertEqual(self.all_organization_dict(), [self.model_to_dict(model, "organization")])
        self.assertEqual(self.bc.database.list_of("events.Event"), [])

    """
    🔽🔽🔽 With academy, call export_event_to_eventbrite, with event
    """

    @patch.object(logging.Logger, "info", log_mock())
    @patch.object(logging.Logger, "error", log_mock())
    @patch.object(actions, "update_or_create_event", update_or_create_event_mock())
    @patch.object(actions, "export_event_to_eventbrite", export_event_to_eventbrite_mock())
    @patch(
        REQUESTS_PATH["request"], apply_requests_request_mock([(200, eventbrite_events_endpoint, EVENTBRITE_EVENTS)])
    )
    def test_sync_org_events__call_export_event_to_eventbrite__with_event(self):
        """Test /answer without auth"""
        import logging
        import breathecode.events.actions as actions

        organization_kwargs = {"eventbrite_id": "1"}
        event_kwargs = {"sync_with_eventbrite": True}
        model = self.generate_models(
            academy=True,
            event=True,
            organization=True,
            event_kwargs=event_kwargs,
            organization_kwargs=organization_kwargs,
        )
        logging.Logger.info.call_args_list = []
        actions.export_event_to_eventbrite.call_args_list = []

        sync_org_events(model["organization"])

        self.assertEqual(actions.export_event_to_eventbrite.call_args_list, [call(model.event, model.organization)])
        self.assertEqual(
            actions.update_or_create_event.call_args_list, [call(EVENTBRITE_EVENTS["events"][0], model.organization)]
        )

        self.assertEqual(logging.Logger.info.call_args_list, [])
        self.assertEqual(logging.Logger.error.call_args_list, [])

        self.assertEqual(self.all_organization_dict(), [self.model_to_dict(model, "organization")])
        self.assertEqual(self.bc.database.list_of("events.Event"), [self.model_to_dict(model, "event")])
