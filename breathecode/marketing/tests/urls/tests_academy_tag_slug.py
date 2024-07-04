"""
Test /academy/tag/slug
"""

from django.urls.base import reverse_lazy
from rest_framework import status
from breathecode.services import datetime_to_iso_format
from ..mixins import MarketingTestCase


def get_serializer(self, tag, data={}):
    return {
        "id": tag.id,
        "tag_type": tag.tag_type,
        "description": tag.description,
        "automation": tag.automation,
        "disputed_reason": tag.disputed_reason,
        "disputed_at": tag.disputed_at,
        **data,
    }


class TestTagSlugView(MarketingTestCase):

    def test_tag_slug__without_auth(self):
        """Test /tag/:slug without auth"""
        url = reverse_lazy("marketing:academy_tag_slug", kwargs={"tag_slug": "slug"})
        response = self.client.put(url)
        json = response.json()
        expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.all_form_entry_dict(), [])

    def test_tag_slug__without_academy_header(self):
        """Test /tag/:slug without academy header"""
        url = reverse_lazy("marketing:academy_tag_slug", kwargs={"tag_slug": "slug"})
        model = self.generate_models(authenticate=True, profile_academy=True, capability="crud_tag", role="potato")

        response = self.client.put(url)
        json = response.json()
        expected = {
            "detail": "Missing academy_id parameter expected for the endpoint url or " "'Academy' header",
            "status_code": 403,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.all_form_entry_dict(), [])

    def test_tag_slug__without_data(self):
        """Test /tag/:slug without data"""
        self.headers(academy=1)
        url = reverse_lazy("marketing:academy_tag_slug", kwargs={"tag_slug": "slug"})
        model = self.generate_models(authenticate=True, profile_academy=True, capability="crud_tag", role="potato")

        response = self.client.put(url)
        json = response.json()
        expected = {"detail": "tag-not-found", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_form_entry_dict(), [])

    """
    🔽🔽🔽 Put
    """

    def test_tag_slug__put(self):
        """Test /tag/:slug"""
        self.headers(academy=1)

        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability="crud_tag",
            role="potato",
            active_campaign_academy=True,
        )

        tag_model = self.generate_models(tag={"ac_academy": model.active_campaign_academy, "slug": "tag_slug"})

        url = reverse_lazy("marketing:academy_tag_slug", kwargs={"tag_slug": "tag_slug"})
        data = {
            "tag_type": "DISCOVERY",
            "description": "descriptive",
        }

        response = self.client.put(url, data, format="json")
        json = response.json()

        expected = get_serializer(self, tag_model.tag, data=data)

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)

    def test_tag_slug__put_many_without_id(self):
        """Test /tag/:slug"""
        self.headers(academy=1)

        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability="crud_tag",
            role="potato",
            active_campaign_academy=True,
        )

        tag_model = self.generate_models(tag={"ac_academy": model.active_campaign_academy, "slug": "tag_slug"})

        url = reverse_lazy("marketing:academy_tag")
        data = [
            {
                "tag_type": "DISCOVERY",
                "description": "descriptive",
            }
        ]

        response = self.client.put(url, data, format="json")
        json = response.json()

        expected = {"detail": "without-id", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_tag_slug__put_many_with_wrong_id(self):
        """Test /tag/:slug"""
        self.headers(academy=1)

        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability="crud_tag",
            role="potato",
            active_campaign_academy=True,
        )

        tag_model = self.generate_models(tag={"ac_academy": model.active_campaign_academy, "slug": "tag_slug"})

        url = reverse_lazy("marketing:academy_tag")
        data = [
            {
                "id": 2,
                "tag_type": "DISCOVERY",
                "description": "descriptive",
            }
        ]

        response = self.client.put(url, data, format="json")
        json = response.json()

        expected = {"detail": "not-found", "status_code": 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_tag_slug__put_many(self):
        """Test /tag/:slug"""
        self.headers(academy=1)

        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability="crud_tag",
            role="potato",
            active_campaign_academy=True,
        )

        tag_model = self.generate_models(tag=2, tag_kwargs={"ac_academy": model.active_campaign_academy})

        url = reverse_lazy("marketing:academy_tag")
        data = [
            {
                "id": 1,
                "tag_type": "DISCOVERY",
            },
            {
                "id": 2,
                "tag_type": "DISCOVERY",
            },
        ]

        response = self.client.put(url, data, format="json")
        json = response.json()

        expected = [get_serializer(self, tag, data=data[i]) for i, tag in enumerate(tag_model.tag)]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
