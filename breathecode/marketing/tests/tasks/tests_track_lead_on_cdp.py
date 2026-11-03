"""CDP lead track runs beside the CRM and does not change storage status."""

import os
from unittest.mock import MagicMock, patch

from breathecode.marketing.actions import register_new_lead
from breathecode.marketing.models import CrmLeadOverride, FormEntry
from breathecode.marketing.tasks import track_lead_on_cdp
from breathecode.marketing.tests.tasks.tests_persist_single_lead import generate_form_entry_kwargs
from breathecode.services.cdp import TRACK_URL, CdpTrackError, build_track_body, get_event_name, track_form_entry

from ..mixins import MarketingTestCase

LEAD_FIELDS = {
    "first_name": "Ana",
    "last_name": "Pérez",
    "email": "ana@ejemplo.com",
    "phone": "+573001112233",
    "country": "CO",
    "course": "full-stack-ft",
    "location": "bogota",
    "language": "es",
    "client_comments": "Quiero el programa",
    "tags": "request-more-info,newsletter",
    "utm_url": "https://4geeks.com/landing/ai-engineering",
    "utm_source": "fb",
    "utm_medium": "paid",
    "utm_campaign": "120249773158400344",
    "utm_content": "120250558071450344",
    "utm_term": "120250115267870344",
    "utm_plan": "upfront",
    "product": "aie",
    "persona": "cc",
    "product_persona": "aie:cc",
    "variant": "b",
    "experiment_id": "workshop:slug:en@2026-10-01",
    "storage_status": "PENDING",
}


class BuildTrackBodyTestSuite(MarketingTestCase):
    def test_body_uses_first_allowlisted_tag_as_event_and_keeps_the_comma_string(self):
        model = self.generate_models(form_entry=generate_form_entry_kwargs(LEAD_FIELDS))
        entry = model.form_entry

        body = build_track_body(entry)

        self.assertEqual(
            body,
            {
                "event": "newsletter",
                "eventId": str(entry.id),
                "source": "breathecode",
                "email": "ana@ejemplo.com",
                "phone": "+573001112233",
                "traits": {"name": "Ana Pérez", "country": "CO"},
                "properties": {
                    "first_name": "Ana",
                    "last_name": "Pérez",
                    "tags": "request-more-info,newsletter",
                    "course": "full-stack-ft",
                    "location": "bogota",
                    "language": "es",
                    "client_comments": "Quiero el programa",
                    "utm_url": "https://4geeks.com/landing/ai-engineering",
                    "utm_source": "fb",
                    "utm_medium": "paid",
                    "utm_campaign": "120249773158400344",
                    "utm_content": "120250558071450344",
                    "utm_term": "120250115267870344",
                    "utm_plan": "upfront",
                    "product": "aie",
                    "persona": "cc",
                    "product_persona": "aie:cc",
                    "variant": "b",
                    "experiment_id": "workshop:slug:en@2026-10-01",
                },
            },
        )

    def test_no_allowlisted_tag_has_no_body(self):
        model = self.generate_models(form_entry=generate_form_entry_kwargs({**LEAD_FIELDS, "tags": "foo, bar"}))

        self.assertIsNone(build_track_body(model.form_entry))

    def test_event_name_is_a_single_allowlisted_tag(self):
        self.assertEqual(get_event_name("request_more_info"), "request_more_info")
        self.assertEqual(get_event_name(" foo , website-lead , newsletter"), "website-lead")
        self.assertIsNone(get_event_name('"request_more_info"'))
        self.assertIsNone(get_event_name(""))
        self.assertIsNone(get_event_name(None))

    def test_empty_tags_have_no_body(self):
        model = self.generate_models(form_entry=generate_form_entry_kwargs({**LEAD_FIELDS, "tags": ""}))

        self.assertIsNone(build_track_body(model.form_entry))


class TrackFormEntryTestSuite(MarketingTestCase):
    def _entry(self, **overrides):
        fields = {**LEAD_FIELDS, **overrides}
        return self.generate_models(form_entry=generate_form_entry_kwargs(fields)).form_entry

    @patch.dict(os.environ, {"CDP_API_KEY": ""}, clear=False)
    @patch("breathecode.services.cdp.requests.post")
    def test_missing_api_key_does_not_post(self, mock_post):
        os.environ.pop("CDP_API_KEY", None)
        entry = self._entry()

        self.assertFalse(track_form_entry(entry))
        mock_post.assert_not_called()

    @patch.dict(os.environ, {"CDP_API_KEY": "cdp-test-key"})
    @patch("breathecode.services.cdp.requests.post")
    def test_empty_tags_do_not_post(self, mock_post):
        entry = self._entry(tags="")

        self.assertFalse(track_form_entry(entry))
        mock_post.assert_not_called()

    @patch.dict(os.environ, {"CDP_API_KEY": "cdp-test-key"})
    @patch("breathecode.services.cdp.requests.post")
    def test_not_allowlisted_tags_do_not_post(self, mock_post):
        entry = self._entry(tags="some-random-tag")

        self.assertFalse(track_form_entry(entry))
        mock_post.assert_not_called()

    @patch.dict(os.environ, {"CDP_API_KEY": "cdp-test-key"})
    @patch("breathecode.services.cdp.requests.post")
    def test_posts_bearer_token_to_the_fixed_url(self, mock_post):
        mock_post.return_value = MagicMock(status_code=202)
        entry = self._entry()

        self.assertTrue(track_form_entry(entry))
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], TRACK_URL)
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer cdp-test-key")
        self.assertEqual(kwargs["headers"]["Content-Type"], "application/json")
        self.assertEqual(kwargs["json"]["event"], "newsletter")
        self.assertEqual(kwargs["json"]["properties"]["tags"], "request-more-info,newsletter")
        self.assertEqual(kwargs["json"]["eventId"], str(entry.id))
        self.assertNotIn("event", kwargs["json"]["properties"])

    @patch.dict(os.environ, {"CDP_API_KEY": "cdp-test-key"})
    @patch("breathecode.services.cdp.requests.post")
    def test_failed_status_raises(self, mock_post):
        mock_post.return_value = MagicMock(status_code=500)
        entry = self._entry()

        with self.assertRaises(CdpTrackError):
            track_form_entry(entry)


class TrackLeadOnCdpTaskTestSuite(MarketingTestCase):
    @patch(
        "breathecode.marketing.tasks.track_form_entry", side_effect=CdpTrackError("CDP track failed with status 500")
    )
    def test_post_failure_does_not_change_storage_status(self, _mock_track):
        model = self.generate_models(
            form_entry=generate_form_entry_kwargs({**LEAD_FIELDS, "storage_status": "PENDING"})
        )
        before = model.form_entry.storage_status
        status_text = model.form_entry.storage_status_text

        # task_manager swallows RetryTask and schedules a reattempt
        track_lead_on_cdp(model.form_entry.id)

        entry = FormEntry.objects.get(id=model.form_entry.id)
        self.assertEqual(entry.storage_status, before)
        self.assertEqual(entry.storage_status_text, status_text)


class RegisterNewLeadCdpEnqueueTestSuite(MarketingTestCase):
    def _payload(self, model, entry=None):
        entry = entry or model.form_entry
        return {
            "location": model.academy.slug,
            "tags": model.tag.slug,
            "automations": model.automation.slug,
            "email": entry.email,
            "first_name": entry.first_name,
            "last_name": entry.last_name,
            "phone": entry.phone,
            "course": entry.course,
            "id": entry.id,
        }

    def _models(self, course="full-stack"):
        return self.generate_models(
            academy=True,
            active_campaign_academy=True,
            tag=True,
            tag_kwargs={"tag_type": "STRONG"},
            automation=True,
            form_entry=generate_form_entry_kwargs({"course": course, "storage_status": "PENDING"}),
        )

    @patch("breathecode.marketing.tasks.track_lead_on_cdp.delay", MagicMock())
    @patch("breathecode.marketing.actions.get_save_leads", return_value="TRUE")
    @patch("breathecode.marketing.actions.send_to_active_campaign")
    def test_duplicate_still_enqueues_track(self, mock_send, _mock_save_leads):
        from breathecode.marketing.tasks import track_lead_on_cdp as task

        model = self._models()
        newer = FormEntry.objects.create(
            email=model.form_entry.email,
            course=model.form_entry.course,
            first_name=model.form_entry.first_name,
            last_name=model.form_entry.last_name,
            phone=model.form_entry.phone,
            tags=model.form_entry.tags,
            academy=model.academy,
            storage_status="PENDING",
        )

        result = register_new_lead(self._payload(model, newer))

        mock_send.assert_not_called()
        self.assertEqual(result.storage_status, "DUPLICATED")
        task.delay.assert_called_once_with(newer.id)

    @patch("breathecode.marketing.tasks.track_lead_on_cdp.delay", MagicMock())
    @patch("breathecode.marketing.actions.get_save_leads", return_value="FALSE")
    @patch("breathecode.marketing.actions.send_to_active_campaign")
    def test_save_leads_false_still_enqueues_track(self, mock_send, _mock_save_leads):
        from breathecode.marketing.tasks import track_lead_on_cdp as task

        model = self._models()

        result = register_new_lead(self._payload(model))

        mock_send.assert_not_called()
        self.assertEqual(result.storage_status, "PERSISTED")
        task.delay.assert_called_once_with(model.form_entry.id)

    @patch("breathecode.marketing.tasks.track_lead_on_cdp.delay", MagicMock())
    @patch("breathecode.marketing.actions.get_save_leads", return_value="TRUE")
    @patch("breathecode.marketing.actions.send_to_active_campaign")
    def test_override_without_destination_still_enqueues_track(self, mock_send, _mock_save_leads):
        from breathecode.marketing.tasks import track_lead_on_cdp as task

        model = self._models(course="ai-flex")
        CrmLeadOverride.objects.create(match_field="course", match_value="ai-flex", is_active=True)

        result = register_new_lead(self._payload(model))

        mock_send.assert_not_called()
        self.assertEqual(result.storage_status, "PERSISTED")
        task.delay.assert_called_once_with(model.form_entry.id)
