"""
Tests for forwarding the tracking fields (variant, experiment_id, product, persona) to the CRMs.
"""

from unittest.mock import patch

from breathecode.marketing.actions import register_new_lead
from breathecode.marketing.tests.tasks.tests_persist_single_lead import generate_form_entry_kwargs
from breathecode.services.activecampaign.client import map_ids
from breathecode.services.brevo import Brevo

from ..mixins import MarketingTestCase

TRACKING_DATA = {
    "variant": "B",
    "experiment_id": "exp-12",
    "product": "full-stack",
    "persona": "career-changer",
    "product_persona": "full-stack-career-changer",
}


class RegisterNewLeadTrackingFieldsTestSuite(MarketingTestCase):
    def _lead_data(self, model, with_tags=True):
        data = {
            "location": model.academy.slug,
            "email": model.form_entry.email,
            "first_name": model.form_entry.first_name,
            "last_name": model.form_entry.last_name,
            "phone": model.form_entry.phone,
            "course": model.form_entry.course,
            "id": model.form_entry.id,
            **TRACKING_DATA,
        }
        if with_tags:
            data["tags"] = model.tag.slug
            data["automations"] = model.automation.slug
        return data

    @patch("breathecode.marketing.actions.get_save_leads", return_value="TRUE")
    @patch("breathecode.marketing.actions.send_to_active_campaign")
    def test_active_campaign_contact_includes_tracking_fields(self, mock_send, _mock_save_leads):
        mock_send.side_effect = lambda form_entry, *args, **kwargs: form_entry

        model = self.generate_models(
            academy=True,
            active_campaign_academy=True,
            tag=True,
            tag_kwargs={"tag_type": "STRONG"},
            automation=True,
            form_entry=generate_form_entry_kwargs({"course": "full-stack", **TRACKING_DATA}),
        )

        register_new_lead(self._lead_data(model))

        mock_send.assert_called_once()
        contact = mock_send.call_args[0][2]
        self.assertEqual(contact["field[160,0]"], "exp-12")
        self.assertEqual(contact["field[161,0]"], "B")
        self.assertEqual(contact["field[162,0]"], "career-changer")
        self.assertEqual(contact["field[163,0]"], "full-stack")
        self.assertNotIn("product_persona", contact)
        self.assertFalse(any("full-stack-career-changer" == value for value in contact.values()))

    @patch("breathecode.marketing.actions.get_save_leads", return_value="TRUE")
    @patch("breathecode.marketing.actions.send_to_brevo")
    def test_brevo_contact_includes_tracking_fields(self, mock_send, _mock_save_leads):
        mock_send.side_effect = lambda form_entry, *args, **kwargs: form_entry

        model = self.generate_models(
            academy=True,
            active_campaign_academy={"crm_vendor": "BREVO"},
            form_entry=generate_form_entry_kwargs({"course": "full-stack", "tags": "", **TRACKING_DATA}),
        )

        register_new_lead(self._lead_data(model, with_tags=False))

        mock_send.assert_called_once()
        contact = mock_send.call_args[0][2]
        self.assertEqual(contact["variant"], "B")
        self.assertEqual(contact["experiment_id"], "exp-12")
        self.assertEqual(contact["product"], "full-stack")
        self.assertEqual(contact["persona"], "career-changer")
        self.assertNotIn("product_persona", contact)


class BrevoTrackingFieldsMappingTestSuite(MarketingTestCase):
    @patch.object(Brevo, "post", return_value={})
    def test_create_contact_maps_tracking_fields_to_brevo_attributes(self, mock_post):
        contact = {
            "email": "a@a.com",
            "first_name": "Rene",
            "last_name": "Descartes",
            "phone": "123",
            "variant": "B",
            "experiment_id": "exp-12",
            "product": "full-stack",
            "persona": "career-changer",
        }

        Brevo("token").create_contact(contact, "some-automation")

        body = mock_post.call_args[1]["request_data"]
        properties = body["contact_properties"]
        self.assertEqual(properties["VARIANT"], "B")
        self.assertEqual(properties["EXPERIMENT_ID"], "exp-12")
        self.assertEqual(properties["BUYER_PRODUCTS"], "full-stack")
        self.assertEqual(properties["BUYER_PERSONAS"], "career-changer")


class MapIdsTrackingFieldsTestSuite(MarketingTestCase):
    def test_contact_fields_map_to_deal_fields(self):
        self.assertEqual(map_ids("160"), "121")
        self.assertEqual(map_ids("161"), "120")
        self.assertEqual(map_ids("162"), "122")
        self.assertEqual(map_ids("163"), "123")
