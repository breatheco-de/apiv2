"""
Test cases for POST/GET /v1/events/academy/event/<event_id>/checkin/bulk
"""

from unittest.mock import MagicMock, patch

from django.urls import reverse_lazy
from rest_framework import status

from breathecode.events.bulk_event_checkin_manager import (
    process_bulk_event_checkin_row,
    set_bulk_job_state,
)

from ..mixins.new_events_tests_case import EventTestCase


class BulkEventCheckinUploadViewTestSuite(EventTestCase):
    """Bulk event check-in import view tests."""

    def _url(self, event_id=1, job_id=None):
        if job_id:
            return reverse_lazy(
                "events:academy_event_checkin_bulk_id",
                kwargs={"event_id": event_id, "job_id": job_id},
            )
        return reverse_lazy("events:academy_event_checkin_bulk", kwargs={"event_id": event_id})

    def test_bulk_post_without_auth(self):
        model = self.generate_models(event=True)
        response = self.client.post(
            self._url(model.event.id),
            {"checkins": [{"email": "a@example.com"}]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_bulk_post_without_capability(self):
        model = self.generate_models(authenticate=True, profile_academy=True, event=True)
        self.headers(academy=model.academy.id)
        response = self.client.post(
            self._url(model.event.id),
            {"checkins": [{"email": "a@example.com"}]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_bulk_post_empty_checkins(self):
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability="crud_eventcheckin",
            role="potato",
            event=True,
        )
        self.headers(academy=model.academy.id)
        response = self.client.post(self._url(model.event.id), {"checkins": []}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("checkins", response.json().get("detail", "").lower())

    def test_bulk_post_missing_email(self):
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability="crud_eventcheckin",
            role="potato",
            event=True,
        )
        self.headers(academy=model.academy.id)
        response = self.client.post(
            self._url(model.event.id),
            {"checkins": [{"first_name": "A"}]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.json().get("detail", "").lower())

    def test_bulk_post_event_not_in_academy(self):
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability="crud_eventcheckin",
            role="potato",
            academy=True,
            event=True,
        )
        other_event = self.generate_models(event=True).event
        self.headers(academy=model.academy.id)
        response = self.client.post(
            self._url(other_event.id),
            {"checkins": [{"email": "a@example.com"}]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_bulk_post_soft_run_returns_200_with_results(self):
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability="crud_eventcheckin",
            role="potato",
            event=True,
        )
        self.headers(academy=model.academy.id)
        response = self.client.post(
            self._url(model.event.id) + "?soft=true",
            {
                "checkins": [
                    {"email": "new@example.com", "attended": False},
                    {"email": "other@example.com", "attended": True},
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["total"], 2)
        self.assertEqual(len(data["results"]), 2)
        self.assertEqual(self.all_event_checkin_dict(), [])

    def test_bulk_post_normal_returns_202_and_job_id(self):
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability="crud_eventcheckin",
            role="potato",
            event=True,
        )
        self.headers(academy=model.academy.id)
        with patch("breathecode.events.tasks.process_bulk_event_checkin_upload") as mock_delay:
            mock_delay.delay = MagicMock(return_value=None)
            response = self.client.post(
                self._url(model.event.id),
                {"checkins": [{"email": "new@example.com"}]},
                format="json",
            )
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertIn("job_id", response.json())
        mock_delay.delay.assert_called_once()

    def test_bulk_get_job_not_found(self):
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability="crud_eventcheckin",
            role="potato",
            event=True,
        )
        self.headers(academy=model.academy.id)
        response = self.client.get(
            self._url(model.event.id, job_id="00000000-0000-0000-0000-000000000001"),
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_process_bulk_event_checkin_row_creates_checkin(self):
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability="crud_eventcheckin",
            role="potato",
            event=True,
        )
        with patch("breathecode.events.tasks.run_event_checkin_marketing_task.delay", MagicMock()) as mock_delay:
            result = process_bulk_event_checkin_row(
                event_id=model.event.id,
                academy_id=model.academy.id,
                row_data={"email": "bulk@example.com", "attended": True},
                run_marketing=True,
            )
        self.assertEqual(result["status"], "created")
        self.assertEqual(result["classification"], "NEW_CHECKIN")
        mock_delay.assert_called_once()
        self.assertEqual(len(self.all_event_checkin_dict()), 1)
        checkin = self.all_event_checkin_dict()[0]
        self.assertEqual(checkin["email"], "bulk@example.com")
        self.assertEqual(checkin["status"], "DONE")

    def test_process_bulk_event_checkin_row_persists_names_without_user(self):
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability="crud_eventcheckin",
            role="potato",
            event=True,
        )
        result = process_bulk_event_checkin_row(
            event_id=model.event.id,
            academy_id=model.academy.id,
            row_data={
                "email": "guest@example.com",
                "first_name": "Guest",
                "last_name": "Visitor",
                "attended": False,
            },
            run_marketing=False,
        )
        self.assertEqual(result["status"], "created")
        checkins = self.all_event_checkin_dict()
        self.assertEqual(len(checkins), 1)
        self.assertEqual(checkins[0]["email"], "guest@example.com")
        self.assertEqual(checkins[0]["first_name"], "Guest")
        self.assertEqual(checkins[0]["last_name"], "Visitor")
        self.assertIsNone(checkins[0]["attendee_id"])

    def test_bulk_get_job_wrong_event_id(self):
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability="crud_eventcheckin",
            role="potato",
            event=True,
        )
        job_id = "11111111-1111-1111-1111-111111111111"
        set_bulk_job_state(
            job_id=job_id,
            status="completed",
            academy_id=model.academy.id,
            event_id=99999,
            total=1,
            processed=1,
            results=[],
        )
        self.headers(academy=model.academy.id)
        response = self.client.get(self._url(model.event.id, job_id=job_id))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
