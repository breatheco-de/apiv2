"""
Test GET /v1/events/ical/student/me — iCal feed for the authenticated user's cohort schedule.
"""

from unittest.mock import MagicMock, patch

from django.urls.base import reverse_lazy
from rest_framework import status

from ..mixins.new_events_tests_case import EventTestCase


class ICalStudentMeTestSuite(EventTestCase):
    """Test ical/student/me"""

    def test_ical_student_me__without_auth__returns_401(self):
        url = reverse_lazy("events:ical_student_me")
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, {"detail": "Authentication credentials were not provided.", "status_code": 401})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch("breathecode.events.tasks.build_live_classes_from_timeslot.delay", MagicMock())
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_ical_student_me__authenticated__same_as_student_id(self):
        """Authenticated user gets the same iCal feed as GET ical/student/<their_id>."""
        device_id_kwargs = {"name": "server"}
        model = self.generate_models(
            authenticate=True,
            academy=True,
            device_id=True,
            device_id_kwargs=device_id_kwargs,
            cohort_user=True,
        )

        user_id = model["user"].id

        url_me = reverse_lazy("events:ical_student_me")
        response_me = self.client.get(url_me)

        url_by_id = reverse_lazy("events:ical_student_id", kwargs={"user_id": user_id})
        response_by_id = self.client.get(url_by_id)

        self.assertEqual(response_me.status_code, status.HTTP_200_OK)
        self.assertEqual(response_by_id.status_code, status.HTTP_200_OK)
        self.assertEqual(response_me.content, response_by_id.content)
        self.assertEqual(response_me["Content-Type"], "text/calendar")
