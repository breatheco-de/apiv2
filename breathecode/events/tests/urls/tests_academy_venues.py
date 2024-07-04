import re
from django.urls.base import reverse_lazy
from ..mixins.new_events_tests_case import EventTestCase


class AcademyVenueTestSuite(EventTestCase):

    def test_academy_venues_no_auth(self):
        self.headers(academy=1)
        url = reverse_lazy("events:academy_venues")

        response = self.client.get(url)
        json = response.json()
        expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 401)

    def test_academy_venues_with_auth(self):
        self.headers(academy=1)
        url = reverse_lazy("events:academy_venues")
        self.generate_models(authenticate=True)

        response = self.client.get(url)
        json = response.json()
        expected = {"detail": "You (user: 1) don't have this capability: read_event for academy 1", "status_code": 403}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 403)

    def test_academy_venues_with_capability(self):
        self.headers(academy=1)
        url = reverse_lazy("events:academy_venues")
        self.generate_models(authenticate=True, profile_academy=True, capability="read_event", role="potato")

        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)

    def test_academy_venues_with_results(self):
        self.headers(academy=1)
        url = reverse_lazy("events:academy_venues")
        model = self.generate_models(
            authenticate=True, profile_academy=True, capability="read_event", role="potato", venue=True
        )

        response = self.client.get(url)
        json = response.json()
        expected = [
            {
                "city": model["venue"].city,
                "id": model["venue"].id,
                "state": model["venue"].state,
                "street_address": model["venue"].street_address,
                "title": model["venue"].title,
                "zip_code": model["venue"].zip_code,
                "updated_at": self.bc.datetime.to_iso_string(model["venue"].updated_at),
            }
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            self.all_venue_dict(),
            [
                {
                    **self.model_to_dict(model, "venue"),
                }
            ],
        )
