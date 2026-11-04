from datetime import timedelta

from django.urls.base import reverse_lazy
from django.utils import timezone
from rest_framework import status

from ..mixins.new_events_tests_case import EventTestCase


class EventSlugRecordingDeniedPlansTestSuite(EventTestCase):
    """GET /v1/events/event/<slug> hides recording_url for denied_plans users."""

    def test_anonymous_still_sees_recording_url(self):
        model = self.bc.database.create(
            event={
                "slug": "career-workshop",
                "recording_url": "https://example.com/recording",
                "status": "FINISHED",
            },
            plan=1,
        )
        model.event.denied_plans.add(model.plan)

        url = reverse_lazy("events:event", kwargs={"event_slug": "career-workshop"})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["recording_url"], "https://example.com/recording")

    def test_authenticated_denied_plan_gets_null_recording_url(self):
        model = self.bc.database.create(
            user=1,
            event={
                "slug": "career-workshop",
                "recording_url": "https://example.com/recording",
                "status": "FINISHED",
            },
            plan={"slug": "plan-apoyo-profesional-aie"},
            plan_financing={
                "status": "FULLY_PAID",
                "plan_expires_at": timezone.now() + timedelta(days=30),
            },
        )
        model.event.denied_plans.add(model.plan)
        model.plan_financing.plans.add(model.plan)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy("events:event", kwargs={"event_slug": "career-workshop"})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.json()["recording_url"])
        self.assertIn(model.plan.slug, response.json()["denied_plans"])

    def test_authenticated_other_plan_still_sees_recording_url(self):
        model = self.bc.database.create(
            user=1,
            event={
                "slug": "career-workshop",
                "recording_url": "https://example.com/recording",
                "status": "FINISHED",
            },
            plan={"slug": "some-other-plan"},
            plan_financing={
                "status": "FULLY_PAID",
                "plan_expires_at": timezone.now() + timedelta(days=30),
            },
        )
        denied = self.bc.database.create(plan={"slug": "other-denied-plan"}).plan
        model.event.denied_plans.add(denied)
        model.plan_financing.plans.add(model.plan)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy("events:event", kwargs={"event_slug": "career-workshop"})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["recording_url"], "https://example.com/recording")
