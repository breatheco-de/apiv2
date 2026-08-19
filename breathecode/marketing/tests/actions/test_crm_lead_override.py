"""Tests for CrmLeadOverride in register_new_lead."""

from django.core.exceptions import ValidationError
from unittest.mock import patch

from breathecode.marketing.actions import register_new_lead
from breathecode.marketing.models import CrmLeadOverride
from breathecode.marketing.tests.tasks.tests_persist_single_lead import generate_form_entry_kwargs

from ..mixins import MarketingTestCase


class CrmLeadOverrideTestSuite(MarketingTestCase):
    def _payload(self, model):
        return {
            "location": model.academy.slug,
            "tags": model.tag.slug,
            "automations": model.automation.slug,
            "email": model.form_entry.email,
            "first_name": model.form_entry.first_name,
            "last_name": model.form_entry.last_name,
            "phone": model.form_entry.phone,
            "course": model.form_entry.course,
            "id": model.form_entry.id,
        }

    def _models(self, course="full-stack"):
        return self.generate_models(
            academy=True,
            active_campaign_academy=True,
            tag=True,
            tag_kwargs={"tag_type": "STRONG"},
            automation=True,
            form_entry=generate_form_entry_kwargs({"course": course}),
        )

    def test_incomplete_destination_cannot_be_saved(self):
        with self.assertRaises(ValidationError):
            CrmLeadOverride.objects.create(
                match_field="course",
                match_value="ai-flex",
                destination_crm_vendor="ACTIVE_CAMPAIGN",
            )

    @patch("breathecode.marketing.actions.get_save_leads", return_value="TRUE")
    @patch("breathecode.marketing.actions.send_to_active_campaign")
    def test_without_override_sends_to_default_crm(self, mock_send, _mock_save_leads):
        mock_send.side_effect = lambda form_entry, *args, **kwargs: form_entry
        model = self._models()

        result = register_new_lead(self._payload(model))

        self.assertEqual(result.storage_status, "PERSISTED")
        mock_send.assert_called_once()
        self.assertEqual(mock_send.call_args.args[1], model.active_campaign_academy)

    @patch("breathecode.marketing.actions.get_save_leads", return_value="TRUE")
    @patch("breathecode.marketing.actions.send_to_active_campaign")
    def test_match_without_destination_does_not_send(self, mock_send, _mock_save_leads):
        model = self._models(course="ai-flex")
        CrmLeadOverride.objects.create(match_field="course", match_value="ai-flex", is_active=True)

        result = register_new_lead(self._payload(model))

        mock_send.assert_not_called()
        self.assertEqual(result.storage_status, "PERSISTED")
        self.assertIn("CrmLeadOverride", result.storage_status_text)

    @patch("breathecode.marketing.actions.get_save_leads", return_value="TRUE")
    @patch("breathecode.marketing.actions.send_to_active_campaign")
    def test_match_with_destination_uses_override_credentials(self, mock_send, _mock_save_leads):
        mock_send.side_effect = lambda form_entry, *args, **kwargs: form_entry
        model = self._models(course="ai-flex")
        CrmLeadOverride.objects.create(
            match_field="course",
            match_value="ai-flex",
            destination_ac_url="https://other.api-us1.com",
            destination_ac_key="other-key",
            destination_crm_vendor="ACTIVE_CAMPAIGN",
            is_active=True,
        )

        result = register_new_lead(self._payload(model))

        self.assertEqual(result.storage_status, "PERSISTED")
        mock_send.assert_called_once()
        dest = mock_send.call_args.args[1]
        self.assertEqual(dest.ac_url, "https://other.api-us1.com")
        self.assertEqual(dest.ac_key, "other-key")
        self.assertEqual(dest.crm_vendor, "ACTIVE_CAMPAIGN")
        self.assertNotEqual(dest.ac_key, model.active_campaign_academy.ac_key)

    @patch("breathecode.marketing.actions.get_save_leads", return_value="TRUE")
    @patch("breathecode.marketing.actions.send_to_active_campaign")
    def test_academy_scoped_override_does_not_apply_to_other_academy(self, mock_send, _mock_save_leads):
        mock_send.side_effect = lambda form_entry, *args, **kwargs: form_entry
        model = self._models(course="ai-flex")
        other = self.generate_models(academy=True)
        CrmLeadOverride.objects.create(
            match_field="course",
            match_value="ai-flex",
            academy=other.academy,
            is_active=True,
        )

        result = register_new_lead(self._payload(model))

        self.assertEqual(result.storage_status, "PERSISTED")
        mock_send.assert_called_once()

    @patch("breathecode.marketing.actions.get_save_leads", return_value="TRUE")
    @patch("breathecode.marketing.actions.send_to_active_campaign")
    def test_inactive_override_is_ignored(self, mock_send, _mock_save_leads):
        mock_send.side_effect = lambda form_entry, *args, **kwargs: form_entry
        model = self._models(course="ai-flex")
        CrmLeadOverride.objects.create(match_field="course", match_value="ai-flex", is_active=False)

        result = register_new_lead(self._payload(model))

        self.assertEqual(result.storage_status, "PERSISTED")
        mock_send.assert_called_once()

    @patch("breathecode.marketing.actions.get_save_leads", return_value="TRUE")
    @patch("breathecode.marketing.actions.send_to_active_campaign")
    def test_specific_academy_wins_over_global(self, mock_send, _mock_save_leads):
        mock_send.side_effect = lambda form_entry, *args, **kwargs: form_entry
        model = self._models(course="ai-flex")
        CrmLeadOverride.objects.create(match_field="course", match_value="ai-flex", is_active=True)
        CrmLeadOverride.objects.create(
            match_field="course",
            match_value="ai-flex",
            academy=model.academy,
            destination_ac_url="https://academy.api-us1.com",
            destination_ac_key="academy-key",
            destination_crm_vendor="ACTIVE_CAMPAIGN",
            is_active=True,
        )

        result = register_new_lead(self._payload(model))

        self.assertEqual(result.storage_status, "PERSISTED")
        dest = mock_send.call_args.args[1]
        self.assertEqual(dest.ac_key, "academy-key")

    @patch("breathecode.marketing.actions.get_save_leads", return_value="TRUE")
    @patch("breathecode.marketing.actions.send_to_active_campaign")
    def test_utm_campaign_match(self, mock_send, _mock_save_leads):
        model = self._models()
        CrmLeadOverride.objects.create(match_field="utm_campaign", match_value="skip-me", is_active=True)
        payload = self._payload(model)
        payload["utm_campaign"] = "Skip-Me"

        result = register_new_lead(payload)

        mock_send.assert_not_called()
        self.assertEqual(result.storage_status, "PERSISTED")
