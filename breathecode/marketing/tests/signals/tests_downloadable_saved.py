from unittest.mock import MagicMock, call, patch

from breathecode.tests.mixins.legacy import LegacyAPITestCase


class TestLead(LegacyAPITestCase):
    """
    🔽🔽🔽 Create with ActiveCampaignAcademy
    """

    @patch("breathecode.marketing.tasks.add_downloadable_slug_as_acp_tag.delay", MagicMock())
    def test_downloadable_saved__create__with_active_campaign_academy(self, enable_signals):
        enable_signals()
        """Test /downloadable/:id/user without auth"""
        from breathecode.marketing.tasks import add_downloadable_slug_as_acp_tag

        base = self.generate_models(academy=True, active_campaign_academy=True, skip_event=True)
        model = self.generate_models(downloadable=True, models=base)

        self.assertEqual(
            self.bc.database.list_of("marketing.Downloadable"), [self.model_to_dict(model, "downloadable")]
        )
        self.assertEqual(add_downloadable_slug_as_acp_tag.delay.call_args_list, [call(1, 1)])
