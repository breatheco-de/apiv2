"""
Collections of mixins used to login in authorize microservice
"""

import os

from django.urls import reverse_lazy
from rest_framework.test import APITestCase

from breathecode.tests.mixins import (
    BreathecodeMixin,
    CacheMixin,
    DatetimeMixin,
    GenerateModelsMixin,
    GenerateQueriesMixin,
    HeadersMixin,
    ICallMixin,
)


class EventTestCase(
    APITestCase,
    GenerateModelsMixin,
    CacheMixin,
    GenerateQueriesMixin,
    HeadersMixin,
    DatetimeMixin,
    ICallMixin,
    BreathecodeMixin,
):
    """AdmissionsTestCase with auth methods"""

    def setUp(self):
        os.environ["API_URL"] = "http://localhost:8000"
        self.generate_queries()
        self.set_test_instance(self)

    def tearDown(self):
        self.clear_cache()

    def check_all_academy_events(self, models=None):
        self.headers(academy=1)
        url = reverse_lazy("events:academy_event")

        if models is None:
            models = [
                self.generate_models(
                    authenticate=True,
                    organization=True,
                    profile_academy=True,
                    capability="read_event",
                    role="potato",
                    syllabus=True,
                    event=True,
                )
            ]

        response = self.client.get(url)
        json = response.json()
        expected = [
            {
                "id": model["event"].id,
                "banner": model["event"].banner,
                "ending_at": self.bc.datetime.to_iso_string(model["event"].ending_at),
                "event_type": model["event"].event_type,
                "excerpt": model["event"].excerpt,
                "lang": model["event"].lang,
                "online_event": model["event"].online_event,
                "tags": model["event"].tags,
                "slug": model["event"].slug,
                "starting_at": self.bc.datetime.to_iso_string(model["event"].starting_at),
                "ended_at": model["event"].ended_at,
                "status": model["event"].status,
                "title": model["event"].title,
                "url": model["event"].url,
                "venue": model["event"].venue,
                "host": model["event"].host,
                "asset_slug": model["event"].asset_slug,
                "capacity": model["event"].capacity,
                "sync_with_eventbrite": model["event"].sync_with_eventbrite,
                "eventbrite_sync_description": model["event"].eventbrite_sync_description,
                "eventbrite_sync_status": model["event"].eventbrite_sync_status,
                "is_public": model["event"].is_public,
            }
            for model in models
        ]

        expected.reverse()

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            self.bc.database.list_of("events.Event"),
            [
                {
                    **self.model_to_dict(model, "event"),
                }
                for model in models
            ],
        )
        return models
