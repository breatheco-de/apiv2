from unittest.mock import MagicMock, call, patch
from breathecode.events.admin import reattempt_eventbrite_webhook
from breathecode.tests.mocks.eventbrite.constants.events import EVENTBRITE_EVENTS
from ..mixins import EventTestCase
from breathecode.events.actions import create_or_update_organizer
import breathecode.events.tasks as tasks


class SyncOrgVenuesTestSuite(EventTestCase):
    """
    🔽🔽🔽 With zero EventbriteWebhook
    """

    @patch("breathecode.events.tasks.async_eventbrite_webhook.delay", MagicMock())
    def test__with_zero_eventbrite_webwooks(self):
        EventbriteWebhook = self.bc.database.get_model("events.EventbriteWebhook")
        queryset = EventbriteWebhook.objects.filter()

        reattempt_eventbrite_webhook(None, None, queryset)

        self.assertEqual(self.bc.database.list_of("events.EventbriteWebhook"), [])
        self.assertEqual(tasks.async_eventbrite_webhook.delay.call_args_list, [])

    """
    🔽🔽🔽 With two EventbriteWebhook
    """

    @patch("breathecode.events.tasks.async_eventbrite_webhook.delay", MagicMock())
    def test__with_two_eventbrite_webwooks(self):
        self.bc.database.create(eventbrite_webhook=2)

        EventbriteWebhook = self.bc.database.get_model("events.EventbriteWebhook")
        queryset = EventbriteWebhook.objects.filter()

        reattempt_eventbrite_webhook(None, None, queryset)

        self.assertEqual(
            self.bc.database.list_of("events.EventbriteWebhook"),
            self.bc.format.to_dict(queryset),
        )
        self.assertEqual(tasks.async_eventbrite_webhook.delay.call_args_list, [call(1), call(2)])
