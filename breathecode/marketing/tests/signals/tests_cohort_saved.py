from unittest.mock import MagicMock, call, patch

from breathecode.tests.mixins.legacy import LegacyAPITestCase


class TestLead(LegacyAPITestCase):
    """
    🔽🔽🔽 Create without ActiveCampaignAcademy
    """

    @patch("breathecode.marketing.tasks.add_cohort_slug_as_acp_tag.delay", MagicMock())
    def test_cohort_saved__create__without_active_campaign_academy(self, enable_signals):
        enable_signals()
        """Test /cohort/:id/user without auth"""
        from breathecode.marketing.tasks import add_cohort_slug_as_acp_tag

        model = self.generate_models(cohort=True)

        self.assertEqual(self.bc.database.list_of("admissions.Cohort"), [self.model_to_dict(model, "cohort")])
        self.assertEqual(add_cohort_slug_as_acp_tag.delay.call_args_list, [])

    """
    🔽🔽🔽 Create with ActiveCampaignAcademy
    """

    @patch("breathecode.marketing.tasks.add_cohort_slug_as_acp_tag.delay", MagicMock())
    def test_cohort_saved__create__with_active_campaign_academy(self, enable_signals):
        enable_signals()
        """Test /cohort/:id/user without auth"""
        from breathecode.marketing.tasks import add_cohort_slug_as_acp_tag

        base = self.generate_models(academy=True, active_campaign_academy=True, skip_cohort=True)
        model = self.generate_models(cohort=True, models=base)

        self.assertEqual(self.bc.database.list_of("admissions.Cohort"), [self.model_to_dict(model, "cohort")])
        self.assertEqual(add_cohort_slug_as_acp_tag.delay.call_args_list, [call(1, 1)])

    """
    🔽🔽🔽 Update with ActiveCampaignAcademy
    """

    @patch("breathecode.marketing.tasks.add_cohort_slug_as_acp_tag.delay", MagicMock())
    def test_cohort_saved__update__with_active_campaign_academy(self, enable_signals):
        enable_signals()
        """Test /cohort/:id/user without auth"""
        from breathecode.marketing.tasks import add_cohort_slug_as_acp_tag

        base = self.generate_models(academy=True, active_campaign_academy=True, skip_cohort=True)
        model = self.generate_models(cohort=True, models=base)

        model.cohort.slug = "they-killed-kenny"
        model.cohort.save()

        self.assertEqual(self.bc.database.list_of("admissions.Cohort"), [self.model_to_dict(model, "cohort")])
        self.assertEqual(add_cohort_slug_as_acp_tag.delay.call_args_list, [call(1, 1)])
