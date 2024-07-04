import logging

from datetime import datetime
from unittest.mock import MagicMock, call, patch

from breathecode.tests.mocks import REQUESTS_PATH, apply_requests_request_mock
from breathecode.tests.mocks.eventbrite.constants.venues import EVENTBRITE_VENUES, get_eventbrite_venues_url
from ..mixins import EventTestCase
import breathecode.events.actions as actions

sync_org_venues = actions.sync_org_venues


def create_or_update_venue_mock(raise_error=False):

    def create_or_update_venue(self, *args, **kwargs):
        if raise_error:
            raise Exception("Random error getting")

    return MagicMock(side_effect=create_or_update_venue)


class SyncOrgVenuesTestSuite(EventTestCase):
    """
    🔽🔽🔽 Without academy
    """

    @patch.object(actions, "create_or_update_venue", create_or_update_venue_mock())
    @patch(
        REQUESTS_PATH["request"],
        apply_requests_request_mock([(200, get_eventbrite_venues_url("1"), EVENTBRITE_VENUES)]),
    )
    def test_sync_org_venues__without_academy(self):
        import logging
        import breathecode.events.actions as actions

        organization_kwargs = {"eventbrite_id": "1"}
        model = self.generate_models(organization=True, organization_kwargs=organization_kwargs)
        logging.Logger.info.call_args_list = []

        with self.assertRaises(Exception) as cm:
            sync_org_venues(model["organization"])

        self.assertEqual(str(cm.exception), "First you must specify to which academy this organization belongs")
        self.assertEqual(actions.create_or_update_venue.call_args_list, [])

        self.assertEqual(self.all_organization_dict(), [self.model_to_dict(model, "organization")])
        self.assertEqual(self.all_venue_dict(), [])

    """
    🔽🔽🔽 With academy
    """

    @patch.object(actions, "create_or_update_venue", create_or_update_venue_mock())
    @patch(
        REQUESTS_PATH["request"],
        apply_requests_request_mock([(200, get_eventbrite_venues_url("1"), EVENTBRITE_VENUES)]),
    )
    def test_sync_org_venues__with_academy(self):
        import logging
        import breathecode.events.actions as actions

        organization_kwargs = {"eventbrite_id": "1"}
        model = self.generate_models(academy=True, organization=True, organization_kwargs=organization_kwargs)
        logging.Logger.info.call_args_list = []

        sync_org_venues(model["organization"])

        self.assertEqual(
            actions.create_or_update_venue.call_args_list,
            [
                call(EVENTBRITE_VENUES["venues"][0], model.organization, force_update=True),
            ],
        )

        self.assertEqual(self.all_organization_dict(), [self.model_to_dict(model, "organization")])
        self.assertEqual(self.all_venue_dict(), [])
