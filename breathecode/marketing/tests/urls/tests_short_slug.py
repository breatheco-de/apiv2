"""
Test PUT /v1/marketing/academy/short/<slug>
"""

from datetime import timedelta
from unittest.mock import patch

from django.urls.base import reverse_lazy
from django.utils import timezone
from rest_framework import status

from breathecode.marketing.models import ShortLink

from ..mixins import MarketingTestCase


class ShortLinkSlugTestSuite(MarketingTestCase):

    def setUp(self):
        super().setUp()
        self.headers(academy=1)

    def _old_short_link(self, **kwargs):
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability="crud_shortlink",
            role="potato",
            short_link=True,
            short_link_kwargs={
                "slug": "ai-engineering",
                "destination": "https://4geeks.com/old",
                **kwargs,
            },
        )
        ShortLink.objects.filter(id=model.short_link.id).update(created_at=timezone.now() - timedelta(days=2))
        model.short_link.refresh_from_db()
        return model

    @patch("breathecode.marketing.serializers.test_link", return_value={"status_code": 200})
    def test_put_old_shortlink_allows_destination_change(self, _mock_test_link):
        """An old shortcut keeps its slug and can point at a new destination."""
        model = self._old_short_link()
        url = reverse_lazy("marketing:short-slug", kwargs={"short_slug": "ai-engineering"})

        response = self.client.put(
            url,
            {"slug": "ai-engineering", "destination": "https://4geeks.com/new"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        model.short_link.refresh_from_db()
        self.assertEqual(model.short_link.slug, "ai-engineering")
        self.assertEqual(model.short_link.destination, "https://4geeks.com/new")

    @patch("breathecode.marketing.serializers.test_link", return_value={"status_code": 200})
    def test_put_old_shortlink_rejects_slug_change(self, _mock_test_link):
        """The public slug of a link older than 1 day stays fixed."""
        model = self._old_short_link()
        url = reverse_lazy("marketing:short-slug", kwargs={"short_slug": "ai-engineering"})

        response = self.client.put(
            url,
            {"slug": "ai-engineering-2", "destination": "https://4geeks.com/old"},
            format="json",
        )
        json = response.json()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(json, {"detail": "update-days-ago", "status_code": 400})
        model.short_link.refresh_from_db()
        self.assertEqual(model.short_link.slug, "ai-engineering")
