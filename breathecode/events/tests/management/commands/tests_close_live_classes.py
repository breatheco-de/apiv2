from datetime import timedelta
import random
from unittest.mock import MagicMock, call, patch
from ...mixins import EventTestCase
import breathecode.events.tasks as tasks
from breathecode.events.management.commands.close_live_classes import Command
from django.utils import timezone

UTC_NOW = timezone.now()
DELTA = timedelta(seconds=60 * random.randint(0, 61), minutes=random.randint(31, 61))


class SyncOrgVenuesTestSuite(EventTestCase):
    """
    🔽🔽🔽 With zero LiveClass
    """

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_without_live_classes(self):
        command = Command()
        command.handle()

        self.assertEqual(self.bc.database.list_of("events.LiveClass"), [])

    """
    🔽🔽🔽 With two LiveClass before ending_at + 30 minutes
    """

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW - DELTA))
    def test_with_two_live_classes_before_ending_at_more_30_minutes__started_at_null(self):
        live_classes = [
            {
                "ending_at": UTC_NOW,
            }
            for n in range(1, 3)
        ]
        model = self.bc.database.create(live_class=live_classes)
        command = Command()
        command.handle()

        self.assertEqual(self.bc.database.list_of("events.LiveClass"), self.bc.format.to_dict(model.live_class))

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW - DELTA))
    def test_with_two_live_classes_before_ending_at_more_30_minutes__started_at_set(self):
        live_classes = [
            {
                "started_at": UTC_NOW,
                "ending_at": UTC_NOW,
            }
            for n in range(1, 3)
        ]
        model = self.bc.database.create(live_class=live_classes)
        command = Command()
        command.handle()

        self.assertEqual(self.bc.database.list_of("events.LiveClass"), self.bc.format.to_dict(model.live_class))

    """
    🔽🔽🔽 With two LiveClass after ending_at + 30 minutes
    """

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW + DELTA))
    def test_with_two_live_classes_after_ending_at_more_30_minutes__started_at_null(self):
        live_classes = [
            {
                "ending_at": UTC_NOW,
            }
            for n in range(1, 3)
        ]
        model = self.bc.database.create(live_class=live_classes)
        command = Command()
        command.handle()

        self.assertEqual(self.bc.database.list_of("events.LiveClass"), self.bc.format.to_dict(model.live_class))

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW + DELTA))
    def test_with_two_live_classes_after_ending_at_more_30_minutes__started_at_set(self):
        live_classes = [
            {
                "started_at": UTC_NOW,
                "ending_at": UTC_NOW,
            }
            for n in range(1, 3)
        ]
        model = self.bc.database.create(live_class=live_classes)
        command = Command()
        command.handle()

        self.assertEqual(
            self.bc.database.list_of("events.LiveClass"),
            [
                {
                    **self.bc.format.to_dict(model.live_class[0]),
                    "ended_at": UTC_NOW + timedelta(minutes=30),
                },
                {
                    **self.bc.format.to_dict(model.live_class[1]),
                    "ended_at": UTC_NOW + timedelta(minutes=30),
                },
            ],
        )
