import random
import logging
from datetime import timedelta
from unittest.mock import MagicMock, call, patch

import pytest
from django.utils import timezone
from breathecode.events import tasks
from ..mixins.new_events_tests_case import EventTestCase

UTC_NOW = timezone.now()


@pytest.fixture(autouse=True)
def setup(db):
    yield


def live_class_item(data={}):
    return {
        "id": 0,
        "cohort_time_slot_id": 0,
        "log": {},
        "remote_meeting_url": "",
        "hash": "",
        "started_at": None,
        "ended_at": None,
        "starting_at": UTC_NOW,
        "ending_at": UTC_NOW,
        **data,
    }


class AcademyEventTestSuite(EventTestCase):

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    def test_mark_live_class_as_started(self):

        model = self.bc.database.create(live_class=1)

        base_model = self.bc.format.to_dict(model.live_class)
        logging.Logger.info.call_args_list = []
        tasks.mark_live_class_as_started(1)

        self.assertEqual(
            logging.Logger.info.call_args_list, [call(f"Starting mark live class {model.live_class.id} as started")]
        )
        self.assertEqual(logging.Logger.error.call_args_list, [])
        self.assertEqual(
            self.bc.database.list_of("events.LiveClass"),
            [
                live_class_item(
                    {
                        **base_model,
                        "started_at": UTC_NOW,
                    }
                ),
            ],
        )

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    def test_mark_live_class_as_started_with_wrong_live_class(self):

        model = self.bc.database.create(live_class=1)

        base_model = self.bc.format.to_dict(model.live_class)
        logging.Logger.info.call_args_list = []
        tasks.mark_live_class_as_started(2)

        self.assertEqual(logging.Logger.info.call_args_list, [call("Starting mark live class 2 as started")])
        self.assertEqual(logging.Logger.error.call_args_list, [call("Live Class 2 not fount")])
        self.assertEqual(
            self.bc.database.list_of("events.LiveClass"),
            [
                live_class_item(
                    {
                        **base_model,
                    }
                ),
            ],
        )
