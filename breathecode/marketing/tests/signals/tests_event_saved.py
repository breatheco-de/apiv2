from unittest.mock import MagicMock, call, patch

from breathecode.tests.mixins.legacy import LegacyAPITestCase


class TestLead(LegacyAPITestCase):
    """
    🔽🔽🔽 Create without slug
    """

    @patch("breathecode.marketing.tasks.add_event_slug_as_acp_tag.delay", MagicMock())
    def test_event_saved__create__without_slug(self, enable_signals):
        enable_signals()
        """Test /cohort/:id/user without auth"""
        from breathecode.marketing.tasks import add_event_slug_as_acp_tag

        model = self.bc.database.create(event=1)

        self.assertEqual(self.bc.database.list_of("events.Event"), [self.bc.format.to_dict(model.event)])
        self.assertEqual(add_event_slug_as_acp_tag.delay.call_args_list, [])

    """
    🔽🔽🔽 Create with slug, without academy
    """

    @patch("breathecode.marketing.tasks.add_event_slug_as_acp_tag.delay", MagicMock())
    def test_event_saved__create__with_slug__without_academy(self, enable_signals):
        enable_signals()
        """Test /cohort/:id/user without auth"""
        from breathecode.marketing.tasks import add_event_slug_as_acp_tag

        event = {"slug": "they-killed-kenny"}
        model = self.bc.database.create(event=event)

        self.assertEqual(self.bc.database.list_of("events.Event"), [self.bc.format.to_dict(model.event)])
        self.assertEqual(add_event_slug_as_acp_tag.delay.call_args_list, [])

    """
    🔽🔽🔽 Create without slug, with academy
    """

    @patch("breathecode.marketing.tasks.add_event_slug_as_acp_tag.delay", MagicMock())
    def test_event_saved__create__without_slug__with_academy(self, enable_signals):
        enable_signals()
        """Test /cohort/:id/user without auth"""
        from breathecode.marketing.tasks import add_event_slug_as_acp_tag

        model = self.bc.database.create(event=1, academy=1)

        self.assertEqual(self.bc.database.list_of("events.Event"), [self.bc.format.to_dict(model.event)])
        self.assertEqual(add_event_slug_as_acp_tag.delay.call_args_list, [])

    """
    🔽🔽🔽 Create with slug, with academy
    """

    @patch("breathecode.marketing.tasks.add_event_slug_as_acp_tag.delay", MagicMock())
    def test_event_saved__create__with_slug__with_academy(self, enable_signals):
        enable_signals()
        """Test /cohort/:id/user without auth"""
        from breathecode.marketing.tasks import add_event_slug_as_acp_tag

        event = {"slug": "they-killed-kenny"}
        model = self.bc.database.create(event=event, academy=1)

        self.assertEqual(self.bc.database.list_of("events.Event"), [self.bc.format.to_dict(model.event)])
        self.assertEqual(add_event_slug_as_acp_tag.delay.call_args_list, [call(1, 1)])
