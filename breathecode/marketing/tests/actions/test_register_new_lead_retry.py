"""
Tests for re-processing FormEntry rows that previously failed in register_new_lead.
"""

from unittest.mock import MagicMock, patch

from breathecode.marketing.actions import register_new_lead, send_to_active_campaign
from breathecode.marketing.tests.tasks.tests_persist_single_lead import generate_form_entry_kwargs

from ..mixins import MarketingTestCase


class RegisterNewLeadRetryTestSuite(MarketingTestCase):
    @patch("breathecode.marketing.actions.get_save_leads", return_value="TRUE")
    @patch("breathecode.marketing.actions.send_to_active_campaign")
    def test_errored_entry_is_persisted_and_status_text_cleared_on_retry(self, mock_send, _mock_save_leads):
        mock_send.side_effect = lambda form_entry, *args, **kwargs: form_entry

        model = self.generate_models(
            academy=True,
            active_campaign_academy=True,
            tag=True,
            tag_kwargs={"tag_type": "STRONG"},
            automation=True,
            form_entry=generate_form_entry_kwargs(
                {
                    "storage_status": "ERROR",
                    "storage_status_text": "Could not save contact in CRM",
                    "course": "full-stack",
                }
            ),
        )

        data = {
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

        result = register_new_lead(data)

        self.assertEqual(result.storage_status, "PERSISTED")
        self.assertEqual(result.storage_status_text, "")
        mock_send.assert_called_once()

        entry = self.bc.database.get("marketing.FormEntry", model.form_entry.id, dict=False)
        self.assertEqual(entry.storage_status, "PERSISTED")
        self.assertEqual(entry.storage_status_text, "")


class SendToActiveCampaignSkipAutomationsTestSuite(MarketingTestCase):
    def _clients(self, mock_old, mock_new, subscriber_id="99"):
        mock_old.return_value.contacts.create_contact.return_value = {"subscriber_id": subscriber_id}
        mock_new.return_value.contacts.add_a_contact_to_an_automation.return_value = {"contacts": [{}]}
        mock_new.return_value.contacts.add_a_tag_to_contact.return_value = {}
        return mock_new.return_value.contacts

    def _contact(self, entry):
        return {
            "email": entry.email,
            "first_name": entry.first_name,
            "last_name": entry.last_name,
            "phone": entry.phone,
        }

    @patch("breathecode.marketing.actions.ActiveCampaignClient")
    @patch("breathecode.marketing.actions.ACOldClient")
    def test_skips_automations_when_ac_contact_id_already_set(self, mock_old, mock_new):
        contacts = self._clients(mock_old, mock_new, subscriber_id="99")
        model = self.generate_models(
            academy=True,
            active_campaign_academy=True,
            tag=True,
            tag_kwargs={"tag_type": "STRONG"},
            form_entry=generate_form_entry_kwargs({"ac_contact_id": "99", "course": "full-stack"}),
        )

        send_to_active_campaign(
            model.form_entry,
            model.active_campaign_academy,
            self._contact(model.form_entry),
            [48],
            [model.tag],
        )

        contacts.add_a_contact_to_an_automation.assert_not_called()
        contacts.add_a_tag_to_contact.assert_called_once()

    @patch("breathecode.marketing.actions.ActiveCampaignClient")
    @patch("breathecode.marketing.actions.ACOldClient")
    def test_enrolls_automations_when_ac_contact_id_is_empty(self, mock_old, mock_new):
        contacts = self._clients(mock_old, mock_new, subscriber_id="100")
        model = self.generate_models(
            academy=True,
            active_campaign_academy=True,
            tag=True,
            tag_kwargs={"tag_type": "STRONG"},
            form_entry=generate_form_entry_kwargs({"ac_contact_id": None, "course": "full-stack"}),
        )

        send_to_active_campaign(
            model.form_entry,
            model.active_campaign_academy,
            self._contact(model.form_entry),
            [48],
            [model.tag],
        )

        contacts.add_a_contact_to_an_automation.assert_called_once()
        contacts.add_a_tag_to_contact.assert_called_once()
