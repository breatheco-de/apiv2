"""Tests for the Caxton workshop tracking webhook."""

import os
from unittest.mock import MagicMock, patch

from django.urls import reverse_lazy
from rest_framework import status

from breathecode.events.models import Event
from breathecode.monitoring import signals

from ..mixins import MonitoringTestCase

SECRET = "caxton-test-secret"
SLUG = "el-mapa-real-del-ai-engineer"


def _payload(event_type, item):
    return {
        "site": "site_4geeks-com",
        "hook_id": "breathecode-workshop-updater",
        "event_type": event_type,
        "events": [item],
    }


def _common_item(**tracking):
    return {
        "id": 4821,
        "type": "entry_common_saved",
        "resource": {
            "path": f"workshop/{SLUG}/_common.yml",
            "contentType": "workshop",
            "slug": SLUG,
            "layer": "common",
        },
        "tracking": {
            "product": "aie",
            "persona": "cc",
            "product_persona": "aie:cc",
            "funnel_stage": "awareness",
            "content_key": f"workshop:{SLUG}",
            **tracking,
        },
    }


def _locale_item(**extra):
    return {
        "id": 4822,
        "type": "entry_locale_saved",
        "resource": {
            "path": f"workshop/{SLUG}/b.en.yml",
            "contentType": "workshop",
            "slug": SLUG,
            "locale": "en",
            "layer": "variant",
        },
        "experiment_id": f"workshop:{SLUG}:en@2026-10-01",
        "variant": "b",
        **extra,
    }


class CaxtonWebhookTestSuite(MonitoringTestCase):
    def setUp(self):
        super().setUp()
        self.env = patch.dict(os.environ, {"CAXTON_WEBHOOK_SECRET": SECRET})
        self.env.start()
        self.url = reverse_lazy("monitoring:caxton_webhook")

    def tearDown(self):
        self.env.stop()
        super().tearDown()

    def _post(self, payload, secret=SECRET):
        if secret is not None:
            self.bc.request.set_headers(x_caxton_secret=secret)
        return self.client.post(self.url, payload, format="json")

    @patch("breathecode.monitoring.signals.caxton_webhook.send", MagicMock())
    def test_missing_secret_header_is_forbidden(self):
        response = self.client.post(self.url, _payload("entry_common_saved", _common_item()), format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.json()["detail"], "not-allowed")
        signals.caxton_webhook.send.assert_not_called()

    @patch("breathecode.monitoring.signals.caxton_webhook.send", MagicMock())
    def test_wrong_secret_is_forbidden(self):
        response = self._post(_payload("entry_common_saved", _common_item()), secret="nope")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        signals.caxton_webhook.send.assert_not_called()

    def test_common_save_updates_tracking_fields(self):
        model = self.generate_models(event={"slug": SLUG, "lang": "en", "title": "Mapa", "variant": "a"})

        response = self._post(_payload("entry_common_saved", _common_item()))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        event = Event.objects.get(id=model.event.id)
        self.assertEqual(event.product, "aie")
        self.assertEqual(event.persona, "cc")
        self.assertEqual(event.product_persona, "aie:cc")
        self.assertEqual(event.variant, "a")
        self.assertIsNone(event.experiment_id)

    def test_locale_save_updates_only_matching_language(self):
        english = self.generate_models(event={"slug": SLUG, "lang": "en", "title": "Mapa"})
        spanish = self.generate_models(event={"slug": SLUG, "lang": "es", "title": "Mapa"})

        response = self._post(_payload("entry_locale_saved", _locale_item()))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        english_event = Event.objects.get(id=english.event.id)
        spanish_event = Event.objects.get(id=spanish.event.id)
        self.assertEqual(english_event.variant, "b")
        self.assertEqual(english_event.experiment_id, f"workshop:{SLUG}:en@2026-10-01")
        self.assertIsNone(spanish_event.variant)
        self.assertIsNone(spanish_event.experiment_id)

    def test_body_without_pipeline_event_key_still_updates(self):
        model = self.generate_models(event={"slug": SLUG, "lang": "en", "title": "Mapa"})
        payload = _payload("entry_common_saved", _common_item())
        payload["event"] = "not-pipeline"

        response = self._post(payload)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Event.objects.get(id=model.event.id).product, "aie")

    def test_non_workshop_and_non_entry_are_ignored(self):
        model = self.generate_models(event={"slug": SLUG, "lang": "en", "title": "Mapa"})
        landing = _common_item()
        landing["resource"] = {**landing["resource"], "contentType": "landing"}
        proposal = _common_item()
        proposal["type"] = "proposal_created"

        self.assertEqual(self._post(_payload("entry_common_saved", landing)).status_code, status.HTTP_200_OK)
        self.assertEqual(self._post(_payload("proposal_created", proposal)).status_code, status.HTTP_200_OK)

        event = Event.objects.get(id=model.event.id)
        self.assertIsNone(event.product)
        self.assertIsNone(event.persona)
        self.assertIsNone(event.product_persona)

    def test_unknown_slug_does_not_create_an_event(self):
        response = self._post(_payload("entry_common_saved", _common_item()))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Event.objects.count(), 0)

    @patch("breathecode.events.models.Event.save", autospec=True)
    def test_unchanged_tracking_does_not_save(self, save):
        self.generate_models(
            event={
                "slug": SLUG,
                "lang": "en",
                "title": "Mapa",
                "product": "aie",
                "persona": "cc",
                "product_persona": "aie:cc",
            }
        )
        save.reset_mock()

        response = self._post(_payload("entry_common_saved", _common_item()))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        save.assert_not_called()
