import logging
from unittest.mock import MagicMock, call, patch
from decimal import Decimal
from breathecode.events.actions import create_or_update_venue
from breathecode.tests.mocks.eventbrite.constants.venues import EVENTBRITE_VENUES, get_eventbrite_venues_url
from ..mixins import EventTestCase


def log_mock():

    def log(self, *args):
        print(*args)

    return MagicMock(side_effect=log)


class SyncOrgVenuesTestSuite(EventTestCase):
    """
    🔽🔽🔽 Without academy
    """

    @patch.object(logging.Logger, "error", log_mock())
    def test_create_or_update_venue__without_academy(self):
        import logging

        organization_kwargs = {"eventbrite_id": "1"}
        model = self.generate_models(organization=True, organization_kwargs=organization_kwargs)

        create_or_update_venue(EVENTBRITE_VENUES["venues"][0], model.organization, force_update=False)

        self.assertEqual(
            logging.Logger.error.call_args_list, [call("The organization Nameless not have a academy assigned")]
        )

        self.assertEqual(self.all_organization_dict(), [self.model_to_dict(model, "organization")])
        self.assertEqual(self.all_venue_dict(), [])

    """
    🔽🔽🔽 With academy
    """

    @patch.object(logging.Logger, "error", log_mock())
    def test_create_or_update_venue__with_academy(self):
        import logging

        organization_kwargs = {"eventbrite_id": "1"}
        model = self.generate_models(academy=True, organization=True, organization_kwargs=organization_kwargs)

        create_or_update_venue(EVENTBRITE_VENUES["venues"][0], model.organization, force_update=False)

        self.assertEqual(logging.Logger.error.call_args_list, [])

        self.assertEqual(self.all_organization_dict(), [self.model_to_dict(model, "organization")])

        event = EVENTBRITE_VENUES["venues"][0]
        self.assertEqual(
            self.all_venue_dict(),
            [
                {
                    "id": 1,
                    "title": event["name"],
                    "street_address": event["address"]["address_1"],
                    "country": event["address"]["country"],
                    "city": event["address"]["city"],
                    "state": event["address"]["region"],
                    "zip_code": str(event["address"]["postal_code"]),
                    "latitude": Decimal("25.758059600000000"),
                    "longitude": Decimal("-80.377022000000000"),
                    "eventbrite_id": event["id"],
                    "eventbrite_url": event["resource_uri"],
                    "academy_id": 1,
                    "organization_id": None,
                    "status": "DRAFT",  # TODO: we want every new venue are saved like 'DRAFT'?
                }
            ],
        )

    """
    🔽🔽🔽 With academy, event exists and is not updated
    """

    @patch.object(logging.Logger, "error", log_mock())
    def test_create_or_update_venue__with_event__is_not_updated(self):
        import logging

        organization_kwargs = {"eventbrite_id": "1"}
        venue_kwargs = {"eventbrite_id": "1"}
        model = self.generate_models(
            academy=True,
            venue=True,
            organization=True,
            venue_kwargs=venue_kwargs,
            organization_kwargs=organization_kwargs,
        )

        create_or_update_venue(EVENTBRITE_VENUES["venues"][0], model.organization, force_update=False)

        self.assertEqual(logging.Logger.error.call_args_list, [])

        self.assertEqual(self.all_organization_dict(), [self.model_to_dict(model, "organization")])
        self.assertEqual(self.all_venue_dict(), [self.model_to_dict(model, "venue")])

    """
    🔽🔽🔽 With academy, event exists and it force updated
    """

    @patch.object(logging.Logger, "error", log_mock())
    def test_create_or_update_venue__with_event__with_force_update(self):
        import logging

        organization_kwargs = {"eventbrite_id": "1"}
        venue_kwargs = {"eventbrite_id": "1"}
        model = self.generate_models(
            academy=True,
            venue=True,
            organization=True,
            venue_kwargs=venue_kwargs,
            organization_kwargs=organization_kwargs,
        )

        create_or_update_venue(EVENTBRITE_VENUES["venues"][0], model.organization, force_update=True)

        self.assertEqual(logging.Logger.error.call_args_list, [])

        self.assertEqual(self.all_organization_dict(), [self.model_to_dict(model, "organization")])

        event = EVENTBRITE_VENUES["venues"][0]
        self.assertEqual(
            self.all_venue_dict(),
            [
                {
                    "id": 1,
                    "title": event["name"],
                    "street_address": event["address"]["address_1"],
                    "country": event["address"]["country"],
                    "city": event["address"]["city"],
                    "state": event["address"]["region"],
                    "zip_code": str(event["address"]["postal_code"]),
                    "latitude": Decimal("25.758059600000000"),
                    "longitude": Decimal("-80.377022000000000"),
                    "eventbrite_id": event["id"],
                    "eventbrite_url": event["resource_uri"],
                    "academy_id": 1,
                    "organization_id": 1,  # this relation is generated by generate_models
                    "status": "DRAFT",  # TODO: we want every new venue are saved like 'DRAFT'?
                }
            ],
        )
