from unittest.mock import MagicMock, call, patch
from ...mixins import EventTestCase
import breathecode.events.tasks as tasks
from breathecode.events.management.commands.rerun_eventbrinte_order_placed import Command


class SyncOrgVenuesTestSuite(EventTestCase):
    """
    🔽🔽🔽 With zero EventbriteWebhook
    """

    @patch("breathecode.events.tasks.async_eventbrite_webhook.delay", MagicMock())
    def test__with_zero_eventbrite_webwooks(self):
        command = Command()
        command.handle()

        self.assertEqual(self.bc.database.list_of("events.EventbriteWebhook"), [])
        self.assertEqual(tasks.async_eventbrite_webhook.delay.call_args_list, [])

    """
    🔽🔽🔽 With two EventbriteWebhook, action does not match
    """

    @patch("breathecode.events.tasks.async_eventbrite_webhook.delay", MagicMock())
    def test__with_two_eventbrite_webwooks__action_does_not_match(self):
        model = self.bc.database.create(eventbrite_webhook=2)

        command = Command()
        command.handle()

        self.assertEqual(
            self.bc.database.list_of("events.EventbriteWebhook"),
            self.bc.format.to_dict(model.eventbrite_webhook),
        )
        self.assertEqual(tasks.async_eventbrite_webhook.delay.call_args_list, [])

    """
    🔽🔽🔽 With two EventbriteWebhook, action match
    """

    @patch("breathecode.events.tasks.async_eventbrite_webhook.delay", MagicMock())
    def test__with_two_eventbrite_webwooks__action_match(self):
        eventbrite_webhook = {"action": "order.placed"}
        model = self.bc.database.create(eventbrite_webhook=(2, eventbrite_webhook))

        command = Command()
        command.handle()

        self.assertEqual(
            self.bc.database.list_of("events.EventbriteWebhook"),
            self.bc.format.to_dict(model.eventbrite_webhook),
        )
        self.assertEqual(tasks.async_eventbrite_webhook.delay.call_args_list, [call(1), call(2)])
