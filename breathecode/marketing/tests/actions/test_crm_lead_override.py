"""Tests for CRM routing in register_new_lead."""

from unittest.mock import patch

from django.core.exceptions import ValidationError

from breathecode.marketing.actions import (
    map_incoming_field_values,
    register_new_lead,
    test_crm_connection as check_crm_connection,
)
from breathecode.marketing.models import CRMConnection, CrmRouting
from breathecode.marketing.tests.tasks.tests_persist_single_lead import generate_form_entry_kwargs
from breathecode.services.brevo import Brevo, BrevoAuthException

from ..mixins import MarketingTestCase


class CrmRoutingTestSuite(MarketingTestCase):
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

    def _connection(self, vendor="ACTIVE_CAMPAIGN", **kwargs):
        defaults = {
            "name": f"{vendor}-{CRMConnection.objects.count()}",
            "crm_vendor": vendor,
            "api_url": "https://other.api-us1.com" if vendor == "ACTIVE_CAMPAIGN" else None,
            "api_key": "other-key",
            "sync_status": "COMPLETED",
        }
        defaults.update(kwargs)
        return CRMConnection.objects.create(**defaults)

    def test_route_requires_a_tested_connection(self):
        connection = self._connection(sync_status="INCOMPLETED")

        with self.assertRaises(ValidationError):
            CrmRouting.objects.create(action="ROUTE", condition="true", connection=connection)

    def test_drop_rejects_connection(self):
        connection = self._connection()

        with self.assertRaises(ValidationError):
            CrmRouting.objects.create(action="DROP", condition="true", connection=connection)

    def test_invalid_cel_condition_cannot_be_saved(self):
        with self.assertRaises(ValidationError):
            CrmRouting.objects.create(action="DROP", condition="lead.course ==")

    def test_non_boolean_cel_condition_cannot_be_saved(self):
        with self.assertRaises(ValidationError):
            CrmRouting.objects.create(action="DROP", condition="lead.course")

    @patch("breathecode.marketing.actions.get_save_leads", return_value="TRUE")
    @patch("breathecode.marketing.actions.send_to_active_campaign")
    def test_without_routing_sends_to_default_crm(self, mock_send, _mock_save_leads):
        mock_send.side_effect = lambda form_entry, *args, **kwargs: form_entry
        model = self._models()

        result = register_new_lead(self._payload(model))

        self.assertEqual(result.storage_status, "PERSISTED")
        mock_send.assert_called_once()
        self.assertEqual(mock_send.call_args.args[1], model.active_campaign_academy)
        self.assertIsNone(result.crm_routing_id)
        self.assertIsNone(result.crm_routed_at)

    @patch("breathecode.marketing.actions.get_save_leads", return_value="TRUE")
    @patch("breathecode.marketing.actions.send_to_active_campaign")
    def test_drop_matching_condition_does_not_send(self, mock_send, _mock_save_leads):
        model = self._models(course="ai-flex")
        routing = CrmRouting.objects.create(action="DROP", condition='lead.course == "ai-flex"')

        result = register_new_lead(self._payload(model))

        mock_send.assert_not_called()
        self.assertEqual(result.storage_status, "PERSISTED")
        self.assertEqual(result.storage_status_text, f"CrmRouting DROP (id={routing.id})")
        self.assertEqual(result.crm_routing_id, routing.id)
        self.assertIsNotNone(result.crm_routed_at)

    @patch("breathecode.marketing.actions.get_save_leads", return_value="TRUE")
    @patch("breathecode.marketing.actions.send_to_active_campaign")
    def test_route_uses_connection_credentials(self, mock_send, _mock_save_leads):
        mock_send.side_effect = lambda form_entry, *args, **kwargs: form_entry
        model = self._models(course="ai-flex")
        connection = self._connection()
        routing = CrmRouting.objects.create(
            action="ROUTE",
            condition='lead.course == "ai-flex"',
            connection=connection,
        )

        result = register_new_lead(self._payload(model))

        self.assertEqual(result.storage_status, "PERSISTED")
        destination = mock_send.call_args.args[1]
        self.assertEqual(destination.ac_url, connection.api_url)
        self.assertEqual(destination.ac_key, connection.api_key)
        self.assertEqual(destination.crm_vendor, "ACTIVE_CAMPAIGN")
        self.assertEqual(result.crm_routing_id, routing.id)
        self.assertIsNotNone(result.crm_routed_at)
        self.assertEqual(result.storage_status_text, f"CrmRouting ROUTE (id={routing.id})")

    @patch("breathecode.marketing.actions.get_save_leads", return_value="TRUE")
    @patch("breathecode.marketing.actions.send_to_active_campaign")
    def test_cel_supports_and_or_conditions(self, mock_send, _mock_save_leads):
        model = self._models(course="ai-flex")
        model.form_entry.country = "CL"
        model.form_entry.utm_source = "google"
        model.form_entry.save(update_fields=["country", "utm_source"])
        CrmRouting.objects.create(
            action="DROP",
            condition=(
                'lead.course == "ai-flex" && ' '(lead.country in ["CL", "AR"] || lead.utm_source == "newsletter")'
            ),
        )

        result = register_new_lead(self._payload(model))

        mock_send.assert_not_called()
        self.assertEqual(result.storage_status, "PERSISTED")

    @patch("breathecode.marketing.actions.get_save_leads", return_value="TRUE")
    @patch("breathecode.marketing.actions.send_to_active_campaign")
    def test_cel_can_use_custom_fields(self, mock_send, _mock_save_leads):
        model = self._models(course="ai-flex")
        model.form_entry.custom_fields = {"company_size": 20}
        model.form_entry.save(update_fields=["custom_fields"])
        CrmRouting.objects.create(
            action="DROP",
            condition='lead.custom.company_size >= 20 && lead.course == "ai-flex"',
        )

        result = register_new_lead(self._payload(model))

        mock_send.assert_not_called()
        self.assertEqual(result.storage_status, "PERSISTED")

    @patch("breathecode.marketing.actions.get_save_leads", return_value="TRUE")
    @patch("breathecode.marketing.actions.send_to_active_campaign")
    def test_academy_scoped_routing_does_not_apply_to_other_academy(self, mock_send, _mock_save_leads):
        mock_send.side_effect = lambda form_entry, *args, **kwargs: form_entry
        model = self._models(course="ai-flex")
        other = self.generate_models(academy=True)
        CrmRouting.objects.create(
            action="DROP",
            condition='lead.course == "ai-flex"',
            academy=other.academy,
        )

        result = register_new_lead(self._payload(model))

        self.assertEqual(result.storage_status, "PERSISTED")
        mock_send.assert_called_once()

    @patch("breathecode.marketing.actions.get_save_leads", return_value="TRUE")
    @patch("breathecode.marketing.actions.send_to_active_campaign")
    def test_specific_academy_wins_over_global(self, mock_send, _mock_save_leads):
        mock_send.side_effect = lambda form_entry, *args, **kwargs: form_entry
        model = self._models(course="ai-flex")
        connection = self._connection(api_key="academy-key")
        CrmRouting.objects.create(action="DROP", condition='lead.course == "ai-flex"')
        CrmRouting.objects.create(
            action="ROUTE",
            condition='lead.course == "ai-flex"',
            academy=model.academy,
            connection=connection,
        )

        result = register_new_lead(self._payload(model))

        self.assertEqual(result.storage_status, "PERSISTED")
        self.assertEqual(mock_send.call_args.args[1].ac_key, "academy-key")

    @patch("breathecode.marketing.actions.get_save_leads", return_value="TRUE")
    @patch("breathecode.marketing.actions.send_to_brevo")
    @patch("breathecode.marketing.actions.send_to_brevo_contact")
    def test_brevo_route_upserts_contact_without_legacy_event(self, mock_contact, mock_legacy_event, _mock_save_leads):
        mock_contact.side_effect = lambda form_entry, *args, **kwargs: form_entry
        model = self._models(course="ai-flex")
        connection = self._connection(vendor="BREVO")
        routing = CrmRouting.objects.create(
            action="ROUTE",
            condition='lead.course == "ai-flex"',
            connection=connection,
        )

        result = register_new_lead(self._payload(model))

        self.assertEqual(result.storage_status, "PERSISTED")
        mock_contact.assert_called_once()
        mock_legacy_event.assert_not_called()
        self.assertEqual(result.crm_routing_id, routing.id)
        self.assertIsNotNone(result.crm_routed_at)
        self.assertEqual(result.storage_status_text, f"CrmRouting ROUTE (id={routing.id})")

    def test_map_incoming_field_values_uses_key_as_incoming(self):
        mapped = map_incoming_field_values(
            {"tags": {"new-conversion": "website-lead"}},
            "tags",
            ["new-conversion", "untouched"],
        )
        self.assertEqual(mapped, ["website-lead", "untouched"])

    def test_mapping_fields_rejects_non_object(self):
        with self.assertRaises(ValidationError):
            CRMConnection.objects.create(
                name="bad-map",
                crm_vendor="BREVO",
                api_key="brevo-key",
                mapping_fields=["not", "an", "object"],
            )

    @patch("breathecode.marketing.actions.get_save_leads", return_value="TRUE")
    @patch("breathecode.marketing.actions.send_to_active_campaign")
    def test_route_maps_incoming_tags_before_ac_lookup(self, mock_send, _mock_save_leads):
        mock_send.side_effect = lambda form_entry, *args, **kwargs: form_entry
        model = self._models()
        connection = self._connection(
            mapping_fields={"tags": {"new-conversion-name": model.tag.slug}},
        )
        CrmRouting.objects.create(action="ROUTE", condition="true", connection=connection)

        payload = self._payload(model)
        payload["tags"] = "new-conversion-name"
        result = register_new_lead(payload)

        self.assertEqual(result.storage_status, "PERSISTED")
        sent_tags = mock_send.call_args.args[4]
        self.assertEqual([tag.slug for tag in sent_tags], [model.tag.slug])

    @patch("breathecode.marketing.actions.get_save_leads", return_value="TRUE")
    @patch("breathecode.marketing.actions.send_to_active_campaign")
    def test_legacy_ac_uses_mapping_from_matching_connection(self, mock_send, _mock_save_leads):
        mock_send.side_effect = lambda form_entry, *args, **kwargs: form_entry
        model = self._models()
        self._connection(
            api_url=model.active_campaign_academy.ac_url,
            api_key=model.active_campaign_academy.ac_key,
            mapping_fields={"tags": {"new-conversion-name": model.tag.slug}},
        )

        payload = self._payload(model)
        payload["tags"] = "new-conversion-name"
        result = register_new_lead(payload)

        self.assertEqual(result.storage_status, "PERSISTED")
        sent_tags = mock_send.call_args.args[4]
        self.assertEqual([tag.slug for tag in sent_tags], [model.tag.slug])

    @patch("breathecode.marketing.actions.Brevo.test_connection")
    def test_brevo_connection_does_not_require_url(self, mock_test):
        mock_test.return_value = {"email": "crm@example.com"}
        connection = CRMConnection.objects.create(
            name="Brevo",
            crm_vendor="BREVO",
            api_key="brevo-key",
        )

        result = check_crm_connection(connection)

        connection.refresh_from_db()
        self.assertEqual(result, {"email": "crm@example.com"})
        self.assertEqual(connection.sync_status, "COMPLETED")
        self.assertEqual(connection.sync_message, "Connection successful")
        self.assertIsNone(connection.api_url)

    @patch("breathecode.marketing.actions.Brevo.test_connection")
    def test_brevo_connection_persists_authentication_error(self, mock_test):
        mock_test.side_effect = BrevoAuthException("Invalid credentials")
        connection = CRMConnection.objects.create(
            name="Invalid Brevo",
            crm_vendor="BREVO",
            api_key="invalid-key",
        )

        with self.assertRaises(BrevoAuthException):
            check_crm_connection(connection)

        connection.refresh_from_db()
        self.assertEqual(connection.sync_status, "INCOMPLETED")
        self.assertEqual(connection.sync_message, "Invalid credentials")
        self.assertIsNotNone(connection.last_interaction_at)

    def test_active_campaign_connection_requires_url(self):
        with self.assertRaises(ValidationError):
            CRMConnection.objects.create(
                name="Invalid AC",
                crm_vendor="ACTIVE_CAMPAIGN",
                api_key="ac-key",
            )

    def test_changing_credentials_requires_a_new_connection_test(self):
        connection = self._connection()

        connection.api_key = "rotated-key"
        connection.save(update_fields=["api_key"])

        connection.refresh_from_db()
        self.assertEqual(connection.sync_status, "INCOMPLETED")
        self.assertIn("must be tested again", connection.sync_message)

    @patch("breathecode.services.brevo.requests.request")
    def test_brevo_upsert_contact_uses_legacy_attributes(self, mock_request):
        response = mock_request.return_value
        response.status_code = 201
        response.json.return_value = {"id": 123}

        result = Brevo("brevo-key").upsert_contact(
            {
                "email": "lead@example.com",
                "first_name": "Ada",
                "last_name": "Lovelace",
                "phone": "+34123456789",
                "course": "ai-flex",
            }
        )

        self.assertEqual(result, {"id": 123})
        kwargs = mock_request.call_args.kwargs
        self.assertEqual(kwargs["method"], "POST")
        self.assertEqual(kwargs["url"], "https://api.brevo.com/v3/contacts")
        self.assertEqual(
            kwargs["json"],
            {
                "email": "lead@example.com",
                "attributes": {
                    "FIRSTNAME": "Ada",
                    "LASTNAME": "Lovelace",
                    "PHONE": "+34123456789",
                    "COURSE": "ai-flex",
                },
                "updateEnabled": True,
                "getId": True,
            },
        )
