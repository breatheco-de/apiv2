import random
from unittest.mock import MagicMock, call, patch
from ....permissions.contexts import event
from ...mixins.new_events_tests_case import EventTestCase

from breathecode.services import LaunchDarkly


def serializer(event):
    author = f"{event.author.first_name} {event.author.last_name} ({event.author.email})" if event.author else "unknown"
    return {
        "id": event.id,
        "slug": event.slug,
        "lang": event.lang,
        "academy": event.academy.slug if event.academy else "unknown",
        "organization": event.organization.name if event.organization else "unknown",
        "published_at": event.published_at,
        "event_type": event.event_type.slug if event.event_type else "unknown",
    }


value = random.randint(1, 1000)


class AcademyEventTestSuite(EventTestCase):

    @patch("ldclient.get", MagicMock())
    @patch("breathecode.services.launch_darkly.client.LaunchDarkly.context", MagicMock(return_value=value))
    def test_make_right_calls(self):
        model = self.bc.database.create(event=1)

        ld = LaunchDarkly()
        result = event(ld, model.event)

        self.assertEqual(
            self.bc.database.list_of("events.Event"),
            [
                self.bc.format.to_dict(model.event),
            ],
        )

        contexts = serializer(model.event)

        self.assertEqual(
            LaunchDarkly.context.call_args_list,
            [
                call("1", model.event.title, "event", contexts),
            ],
        )

        self.assertEqual(result, value)
