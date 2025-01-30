import logging
import os
import random
from unittest.mock import MagicMock, PropertyMock, call, patch
from uuid import UUID

from django.utils import timezone

import breathecode.events.actions as actions
from breathecode.tests.mocks.eventbrite.constants.events import EVENTBRITE_EVENTS

from ..mixins import EventTestCase

update_or_create_event = actions.update_or_create_event
sync_desc = "2021-11-23 09:10:58.295264+00:00"
status_map = {
    "draft": "DRAFT",
    "live": "ACTIVE",
    "completed": "COMPLETED",
    "started": "ACTIVE",
    "ended": "ACTIVE",
    "canceled": "DELETED",
}

seed = os.urandom(16)
uuid = UUID(bytes=seed, version=4)


def log_mock():

    def log(self, *args):
        print(*args)

    return MagicMock(side_effect=log)


def create_or_update_venue_mock(raise_error=False):

    def create_or_update_venue(*args, **kwargs):
        pass

    return MagicMock(side_effect=create_or_update_venue)


def create_or_update_organizer_mock(raise_error=False):

    def create_or_update_organizer(*args, **kwargs):
        pass

    return MagicMock(side_effect=create_or_update_organizer)


def get_current_iso_string_mock():

    def get_current_iso_string():
        return sync_desc

    return MagicMock(side_effect=get_current_iso_string)


class SyncOrgVenuesTestSuite(EventTestCase):
    """
    🔽🔽🔽 Data is None
    """

    @patch.object(logging.Logger, "warning", log_mock())
    @patch.object(logging.Logger, "error", log_mock())
    @patch.object(actions, "create_or_update_venue", create_or_update_venue_mock())
    @patch.object(actions, "create_or_update_organizer", create_or_update_organizer_mock())
    @patch.object(actions, "update_event_description_from_eventbrite", MagicMock())
    def test_update_or_create_event__data_is_none(self):
        import logging

        import breathecode.events.actions as actions

        organization_kwargs = {"eventbrite_id": "1"}
        model = self.generate_models(organization=True, organization_kwargs=organization_kwargs)

        update_or_create_event(None, model.organization)

        self.assertEqual(logging.Logger.warning.call_args_list, [call("Ignored event")])
        self.assertEqual(logging.Logger.error.call_args_list, [])

        self.assertEqual(actions.create_or_update_venue.call_args_list, [])
        self.assertEqual(actions.create_or_update_organizer.call_args_list, [])
        self.assertEqual(actions.update_event_description_from_eventbrite.call_args_list, [])

        self.assertEqual(self.all_organization_dict(), [self.model_to_dict(model, "organization")])
        self.assertEqual(self.bc.database.list_of("events.Event"), [])

    """
    🔽🔽🔽 Without academy
    """

    @patch.object(logging.Logger, "warning", log_mock())
    @patch.object(logging.Logger, "error", log_mock())
    @patch.object(actions, "create_or_update_venue", create_or_update_venue_mock())
    @patch.object(actions, "create_or_update_organizer", create_or_update_organizer_mock())
    @patch.object(actions, "update_event_description_from_eventbrite", MagicMock())
    def test_update_or_create_event__without_academy(self):
        import logging

        import breathecode.events.actions as actions

        organization_kwargs = {"eventbrite_id": "1"}
        model = self.generate_models(organization=True, organization_kwargs=organization_kwargs)

        update_or_create_event(EVENTBRITE_EVENTS["events"][0], model.organization)

        self.assertEqual(logging.Logger.warning.call_args_list, [])
        self.assertEqual(
            logging.Logger.error.call_args_list, [call("The organization Nameless not have a academy assigned")]
        )

        self.assertEqual(actions.create_or_update_venue.call_args_list, [])
        self.assertEqual(actions.create_or_update_organizer.call_args_list, [])
        self.assertEqual(actions.update_event_description_from_eventbrite.call_args_list, [])

        self.assertEqual(self.all_organization_dict(), [self.model_to_dict(model, "organization")])
        self.assertEqual(self.bc.database.list_of("events.Event"), [])

    """
    🔽🔽🔽 With academy
    """

    @patch.object(logging.Logger, "warning", log_mock())
    @patch.object(logging.Logger, "error", log_mock())
    @patch.object(actions, "get_current_iso_string", get_current_iso_string_mock())
    @patch.object(actions, "create_or_update_venue", create_or_update_venue_mock())
    @patch.object(actions, "create_or_update_organizer", create_or_update_organizer_mock())
    @patch.object(actions, "update_event_description_from_eventbrite", MagicMock())
    @patch("breathecode.events.signals.event_saved.send_robust", MagicMock())
    @patch("uuid.uuid4", PropertyMock(MagicMock=uuid))
    @patch("os.urandom", MagicMock(return_value=seed))
    def test_update_or_create_event__with_academy(self):
        import logging

        import breathecode.events.actions as actions

        organization_kwargs = {"eventbrite_id": "1"}
        model = self.generate_models(academy=True, organization=True, organization_kwargs=organization_kwargs)

        update_or_create_event(EVENTBRITE_EVENTS["events"][0], model.organization)
        event = EVENTBRITE_EVENTS["events"][0]

        self.assertEqual(logging.Logger.warning.call_args_list, [])
        self.assertEqual(logging.Logger.error.call_args_list, [])

        self.assertEqual(actions.create_or_update_venue.call_args_list, [call(event["venue"], model.organization)])
        self.assertEqual(
            actions.create_or_update_organizer.call_args_list,
            [call(event["organizer"], model.organization, force_update=True)],
        )

        self.assertEqual(
            actions.update_event_description_from_eventbrite.call_args_list,
            [
                call(self.bc.database.get("events.Event", 1, dict=False)),
            ],
        )
        self.assertEqual(self.all_organization_dict(), [self.model_to_dict(model, "organization")])

        event = EVENTBRITE_EVENTS["events"][0]
        kwargs = {
            "id": 1,
            "description": None,
            "excerpt": event["description"]["text"],
            "title": event["name"]["text"],
            "lang": None,
            "url": event["url"],
            "banner": event["logo"]["url"],
            "tags": "",
            "slug": f"geektalks-presentacion-de-proyectos-finales-{uuid}",
            "capacity": event["capacity"],
            "currency": event["currency"],
            "starting_at": self.iso_to_datetime(event["start"]["utc"]),
            "ending_at": self.iso_to_datetime(event["end"]["utc"]),
            "ended_at": None,
            "host": None,
            "academy_id": 1,
            "organization_id": model.organization.id,
            "author_id": None,
            "online_event": event["online_event"],
            "venue_id": None,
            "event_type_id": None,
            "eventbrite_id": event["id"],
            "eventbrite_url": event["url"],
            "status": status_map[event["status"]],
            "eventbrite_status": event["status"],
            # organizer: organizer,
            "published_at": self.iso_to_datetime(event["published"]),
            "sync_with_eventbrite": True,
            "eventbrite_sync_status": "PERSISTED",
            "eventbrite_organizer_id": None,
            "live_stream_url": None,
            "eventbrite_sync_description": "2021-11-23 09:10:58.295264+00:00",
            "host_user_id": None,
            "free_for_bootcamps": True,
            "live_stream_url": None,
            "asset_slug": None,
            "free_for_all": False,
            "uuid": uuid,
            "is_public": True,
        }

        self.assertEqual(self.bc.database.list_of("events.Event"), [kwargs])

    """
    🔽🔽🔽 With academy and event
    """

    @patch.object(logging.Logger, "warning", log_mock())
    @patch.object(logging.Logger, "error", log_mock())
    @patch.object(actions, "get_current_iso_string", get_current_iso_string_mock())
    @patch.object(actions, "create_or_update_venue", create_or_update_venue_mock())
    @patch.object(actions, "create_or_update_organizer", create_or_update_organizer_mock())
    @patch.object(actions, "update_event_description_from_eventbrite", MagicMock())
    @patch("uuid.uuid4", PropertyMock(MagicMock=uuid))
    @patch("os.urandom", MagicMock(return_value=seed))
    def test_update_or_create_event__with_event(self):
        import logging

        import breathecode.events.actions as actions

        organization_kwargs = {"eventbrite_id": "1"}
        event_kwargs = {"eventbrite_id": "1"}
        model = self.generate_models(
            event=True,
            academy=True,
            organization=True,
            event_kwargs=event_kwargs,
            organization_kwargs=organization_kwargs,
        )

        update_or_create_event(EVENTBRITE_EVENTS["events"][0], model.organization)
        event = EVENTBRITE_EVENTS["events"][0]

        self.assertEqual(logging.Logger.warning.call_args_list, [])
        self.assertEqual(logging.Logger.error.call_args_list, [])

        self.assertEqual(actions.create_or_update_venue.call_args_list, [call(event["venue"], model.organization)])
        self.assertEqual(
            actions.create_or_update_organizer.call_args_list,
            [call(event["organizer"], model.organization, force_update=True)],
        )

        self.assertEqual(
            actions.update_event_description_from_eventbrite.call_args_list,
            [
                call(model.event),
            ],
        )

        self.assertEqual(self.all_organization_dict(), [self.model_to_dict(model, "organization")])

        event = EVENTBRITE_EVENTS["events"][0]
        kwargs = {
            "id": 1,
            "description": None,
            "excerpt": event["description"]["text"],
            "title": event["name"]["text"],
            "currency": event["currency"],
            "lang": None,
            "url": EVENTBRITE_EVENTS["events"][0]["url"],
            "banner": event["logo"]["url"],
            "capacity": event["capacity"],
            "tags": "",
            "slug": f"geektalks-presentacion-de-proyectos-finales-{uuid}",
            "starting_at": self.iso_to_datetime(event["start"]["utc"]),
            "ending_at": self.iso_to_datetime(event["end"]["utc"]),
            "ended_at": None,
            "host": None,
            "academy_id": 1,
            "organization_id": model.organization.id,
            "author_id": None,
            "online_event": event["online_event"],
            "venue_id": None,
            "event_type_id": None,
            "eventbrite_id": event["id"],
            "eventbrite_url": event["url"],
            "status": status_map[event["status"]],
            "eventbrite_status": event["status"],
            # organizer: organizer,
            "published_at": self.iso_to_datetime(event["published"]),
            "sync_with_eventbrite": False,
            "eventbrite_sync_status": "PERSISTED",
            "eventbrite_organizer_id": None,
            "live_stream_url": None,
            "eventbrite_sync_description": "2021-11-23 09:10:58.295264+00:00",
            "host_user_id": None,
            "free_for_bootcamps": True,
            "live_stream_url": None,
            "asset_slug": None,
            "free_for_all": False,
            "uuid": uuid,
            "is_public": True,
        }

        self.assertEqual(self.bc.database.list_of("events.Event"), [kwargs])
