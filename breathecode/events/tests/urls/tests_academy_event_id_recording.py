from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.urls.base import reverse_lazy
from django.utils import timezone

from ..mixins.new_events_tests_case import EventTestCase


class AcademyEventRecordingTestSuite(EventTestCase):

    @patch("breathecode.marketing.signals.downloadable_saved.send_robust", MagicMock())
    @patch("breathecode.events.tasks.send_event_recording_notification.delay", MagicMock())
    def test_publish_recording_on_finished_event(self):
        self.headers(academy=1)
        url = reverse_lazy("events:academy_event_id_recording", kwargs={"event_id": 1})
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability="crud_event",
            role="potato",
            syllabus=True,
            event=True,
            event_kwargs={
                "status": "FINISHED",
                "ending_at": timezone.now() - timedelta(hours=1),
                "recording_url": None,
            },
        )

        data = {"recording_url": "https://example.com/recording"}
        response = self.client.put(url, data, format="json")

        self.assertEqual(response.status_code, 200)
        model["event"].refresh_from_db()
        self.assertEqual(model["event"].recording_url, "https://example.com/recording")

    @patch("breathecode.marketing.signals.downloadable_saved.send_robust", MagicMock())
    def test_publish_recording_rejects_not_finished_event(self):
        self.headers(academy=1)
        url = reverse_lazy("events:academy_event_id_recording", kwargs={"event_id": 1})
        self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability="crud_event",
            role="potato",
            syllabus=True,
            event=True,
            event_kwargs={
                "status": "ACTIVE",
                "ending_at": timezone.now() + timedelta(hours=2),
            },
        )

        data = {"recording_url": "https://example.com/recording"}
        response = self.client.put(url, data, format="json")
        json = response.json()

        self.assertEqual(response.status_code, 400)
        self.assertEqual(json["slug"], "event-not-finished")

    @patch("breathecode.marketing.signals.downloadable_saved.send_robust", MagicMock())
    def test_publish_recording_rejects_invalid_url(self):
        self.headers(academy=1)
        url = reverse_lazy("events:academy_event_id_recording", kwargs={"event_id": 1})
        self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability="crud_event",
            role="potato",
            syllabus=True,
            event=True,
            event_kwargs={
                "status": "FINISHED",
                "ending_at": timezone.now() - timedelta(hours=1),
            },
        )

        data = {"recording_url": "not-a-valid-url"}
        response = self.client.put(url, data, format="json")
        json = response.json()

        self.assertEqual(response.status_code, 400)
        self.assertEqual(json["slug"], "invalid-recording-url")

    @patch("breathecode.marketing.signals.downloadable_saved.send_robust", MagicMock())
    def test_publish_recording_without_capability(self):
        self.headers(academy=1)
        url = reverse_lazy("events:academy_event_id_recording", kwargs={"event_id": 1})
        self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability="read_event",
            role="potato",
            syllabus=True,
            event=True,
            event_kwargs={
                "status": "FINISHED",
                "ending_at": timezone.now() - timedelta(hours=1),
            },
        )

        data = {"recording_url": "https://example.com/recording"}
        response = self.client.put(url, data, format="json")
        json = response.json()

        self.assertEqual(response.status_code, 403)
        self.assertIn("crud_event", json["detail"])
