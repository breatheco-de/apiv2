"""
read_dashboard keeps the academy only when it was resolved and it is white label.
"""

from unittest.mock import patch

from django.core.cache import cache
from django.urls.base import reverse_lazy
from rest_framework import status

from ...mixins import MediaTestCase


class MediaTestSuite(MediaTestCase):

    def setUp(self):
        super().setUp()
        cache.clear()

    def test_white_label_academy_is_stored(self):
        model = self.bc.database.create(user=1, academy={"white_labeled": True})
        self.client.force_authenticate(model.user)

        url = reverse_lazy("v2:activity:me_activity_slug", kwargs={"activity_slug": "read_dashboard"})

        with patch("breathecode.activity.views.add_activity.delay") as delay:
            response = self.client.post(url, {}, format="json", headers={"Academy": str(model.academy.id)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(delay.call_args.kwargs["academy_id"], model.academy.id)
        self.assertEqual(delay.call_args.kwargs["kind"], "read_dashboard")

    def test_white_label_academy_from_origin_is_stored(self):
        model = self.bc.database.create(
            user=1,
            academy={"white_labeled": True, "website_url": "https://uni.example"},
        )
        self.client.force_authenticate(model.user)

        url = reverse_lazy("v2:activity:me_activity_slug", kwargs={"activity_slug": "read_dashboard"})

        with patch("breathecode.activity.views.add_activity.delay") as delay:
            response = self.client.post(url, {}, format="json", headers={"Origin": "https://uni.example"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(delay.call_args.kwargs["academy_id"], model.academy.id)

    def test_non_white_label_academy_is_dropped(self):
        model = self.bc.database.create(user=1, academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("v2:activity:me_activity_slug", kwargs={"activity_slug": "read_dashboard"})

        with patch("breathecode.activity.views.add_activity.delay") as delay:
            response = self.client.post(url, {}, format="json", headers={"Academy": str(model.academy.id)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(delay.call_args.kwargs["academy_id"])

    def test_missing_academy_stays_empty(self):
        model = self.bc.database.create(user=1, academy={"white_labeled": True})
        self.client.force_authenticate(model.user)

        url = reverse_lazy("v2:activity:me_activity_slug", kwargs={"activity_slug": "read_dashboard"})

        with patch("breathecode.activity.views.add_activity.delay") as delay:
            response = self.client.post(url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(delay.call_args.kwargs["academy_id"])
