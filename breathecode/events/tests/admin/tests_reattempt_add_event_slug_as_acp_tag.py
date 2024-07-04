from unittest.mock import patch, MagicMock, call
from breathecode.events.admin import reattempt_add_event_slug_as_acp_tag
from breathecode.tests.mocks.django_contrib import DJANGO_CONTRIB_PATH, apply_django_contrib_messages_mock
from breathecode.career.models import Job
from breathecode.career.admin import get_was_published_date_from_string_admin
from ..mixins import EventTestCase
from django.http.request import HttpRequest
import breathecode.marketing.tasks as tasks


class ParseDateAdminTestSuite(EventTestCase):
    """
    🔽🔽🔽 With zero Event
    """

    @patch("breathecode.marketing.tasks.add_event_slug_as_acp_tag.delay", MagicMock())
    def test_with_zero_events(self):

        Event = self.bc.database.get_model("events.Event")
        queryset = Event.objects.filter()

        reattempt_add_event_slug_as_acp_tag(None, None, queryset)

        self.assertEqual(tasks.add_event_slug_as_acp_tag.delay.call_args_list, [])

    """
    🔽🔽🔽 With two Event
    """

    @patch("breathecode.marketing.tasks.add_event_slug_as_acp_tag.delay", MagicMock())
    def test_with_two_event(self):

        self.bc.database.create(event=2)

        Event = self.bc.database.get_model("events.Event")
        queryset = Event.objects.filter()

        reattempt_add_event_slug_as_acp_tag(None, None, queryset)

        self.assertEqual(tasks.add_event_slug_as_acp_tag.delay.call_args_list, [])

    """
    🔽🔽🔽 With zero Event with Academy
    """

    @patch("breathecode.marketing.tasks.add_event_slug_as_acp_tag.delay", MagicMock())
    def test_with_zero_events__with_academy(self):

        self.bc.database.create(academy=1)

        Event = self.bc.database.get_model("events.Event")
        queryset = Event.objects.filter()

        reattempt_add_event_slug_as_acp_tag(None, None, queryset)

        self.assertEqual(tasks.add_event_slug_as_acp_tag.delay.call_args_list, [])

    """
    🔽🔽🔽 With two Event with Academy
    """

    @patch("breathecode.marketing.tasks.add_event_slug_as_acp_tag.delay", MagicMock())
    def test_with_two_events__with_academy(self):

        self.bc.database.create(event=2, academy=1)

        Event = self.bc.database.get_model("events.Event")
        queryset = Event.objects.filter()

        reattempt_add_event_slug_as_acp_tag(None, None, queryset)

        self.assertEqual(
            tasks.add_event_slug_as_acp_tag.delay.call_args_list,
            [
                call(1, 1, force=True),
                call(2, 1, force=True),
            ],
        )
