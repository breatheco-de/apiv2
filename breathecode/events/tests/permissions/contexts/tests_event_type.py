import random
from unittest.mock import MagicMock, call, patch
from ....permissions.contexts import event_type
from ...mixins.new_events_tests_case import EventTestCase

from breathecode.services import LaunchDarkly


def serializer(event_type):
    return {
        'id': event_type.id,
        'slug': event_type.slug,
        'name': event_type.name,
        'academy': event_type.academy.slug,
        'lang': event_type.lang,
        'allow_shared_creation': event_type.allow_shared_creation,
    }


value = random.randint(1, 1000)


class AcademyEventTestSuite(EventTestCase):

    @patch('ldclient.get', MagicMock())
    @patch('breathecode.services.launch_darkly.client.LaunchDarkly.context', MagicMock(return_value=value))
    def test_make_right_calls(self):
        kwargs = {'icon_url': self.bc.fake.url()}
        model = self.bc.database.create(event_type=kwargs)

        ld = LaunchDarkly()
        result = event_type(ld, model.event_type)

        self.assertEqual(self.bc.database.list_of('events.EventType'), [
            self.bc.format.to_dict(model.event_type),
        ])

        contexts = serializer(model.event_type)

        self.assertEqual(LaunchDarkly.context.call_args_list, [
            call('event-type-1', model.event_type.name, 'event-type-information', contexts),
        ])

        self.assertEqual(result, value)
