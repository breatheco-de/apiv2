"""
Test /activecampaign
"""

from django.urls.base import reverse_lazy
from rest_framework import status
from breathecode.services import datetime_to_iso_format
from ..mixins import MarketingTestCase


def get_serializer(active_campaign_academy, academy, event_attendancy_automation=None, data={}):
    return {
        "id": active_campaign_academy.id,
        "ac_key": active_campaign_academy.ac_key,
        "ac_url": active_campaign_academy.ac_url,
        "duplicate_leads_delta_avoidance": str(active_campaign_academy.duplicate_leads_delta_avoidance.total_seconds()),
        "sync_status": active_campaign_academy.sync_status,
        "sync_message": active_campaign_academy.sync_message,
        "last_interaction_at": active_campaign_academy.last_interaction_at,
        "event_attendancy_automation": event_attendancy_automation,
        "academy": {
            "id": academy.id,
            "slug": academy.slug,
            "name": academy.name,
        },
        "created_at": datetime_to_iso_format(active_campaign_academy.created_at),
        "updated_at": datetime_to_iso_format(active_campaign_academy.updated_at),
        **data,
    }


class ActiveCampaignTestSuite(MarketingTestCase):
    """Test /activecampaign"""

    """
    🔽🔽🔽 without Auth
    """

    def test_active_campaign_without_auth(self):
        """Test /activecampaign without auth"""
        url = reverse_lazy("marketing:activecampaign")
        response = self.client.get(url)
        json = response.json()
        expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.all_active_campaign_academy_dict(), [])

    """
    🔽🔽🔽 without capability
    """

    def test_without_capability(self):
        """Test /activecampaign without data"""
        url = reverse_lazy("marketing:activecampaign")
        self.generate_models(
            authenticate=True,
            academy=True,
            profile_academy=True,
        )
        self.headers(academy=1)
        response = self.client.get(url)
        json = response.json()
        expected = {"detail": "You (user: 1) don't have this capability: read_lead for academy 1", "status_code": 403}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    """
    🔽🔽🔽 without academy headers
    """

    def test_without_academy_header(self):
        """Test /activecampaign without data"""
        url = reverse_lazy("marketing:activecampaign")
        self.generate_models(
            authenticate=True,
            academy=True,
            profile_academy=True,
        )
        response = self.client.get(url)
        json = response.json()
        expected = {
            "detail": "Missing academy_id parameter expected for the endpoint url or 'Academy' header",
            "status_code": 403,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    """
    🔽🔽🔽 without data
    """

    def test_without_data(self):
        """Test /activecampaign without data"""
        url = reverse_lazy("marketing:activecampaign")
        self.generate_models(
            authenticate=True,
            academy=True,
            profile_academy=True,
            capability="read_lead",
            role="potato",
        )
        self.headers(academy=1)
        response = self.client.get(url)
        json = response.json()
        expected = {"detail": "Active Campaign Academy not found", "status_code": 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.all_active_campaign_academy_dict(), [])

    """
    🔽🔽🔽 with data
    """

    def test_active_campaign(self):
        """Test /activecampaign"""
        url = reverse_lazy("marketing:activecampaign")
        model = self.generate_models(
            authenticate=True,
            academy=True,
            profile_academy=True,
            active_campaign_academy=True,
            capability="read_lead",
            role="potato",
        )
        self.headers(academy=1)
        response = self.client.get(url)
        json = response.json()

        expected = get_serializer(model.active_campaign_academy, academy=model.academy)

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    """
    🔽🔽🔽 Post without academy
    """

    def test_post_active_campaign_without_academy(self):
        """Test /activecampaign"""
        url = reverse_lazy("marketing:activecampaign")
        model = self.generate_models(
            authenticate=True,
            academy=True,
            profile_academy=True,
            capability="crud_lead",
            role="potato",
        )
        data = {"ac_key": "55555555", "ac_url": "https://www.potato.com/"}
        response = self.client.post(url, data)
        json = response.json()

        expected = {
            "detail": "Missing academy_id parameter expected for the endpoint url or 'Academy' header",
            "status_code": 403,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    """
    🔽🔽🔽 Post
    """

    def test_post_active_campaign(self):
        """Test /activecampaign"""
        url = reverse_lazy("marketing:activecampaign")
        model = self.generate_models(
            authenticate=True,
            academy=True,
            profile_academy=True,
            capability="crud_lead",
            role="potato",
        )
        self.headers(academy=1)
        data = {"ac_key": "55555555", "ac_url": "https://www.potato.com/"}
        response = self.client.post(url, data)
        json = response.json()

        self.assertDatetime(json["created_at"])
        self.assertDatetime(json["updated_at"])

        del json["created_at"]
        del json["updated_at"]

        expected = {
            "id": 1,
            "event_attendancy_automation": None,
            "last_interaction_at": None,
            "sync_message": None,
            "sync_status": "INCOMPLETED",
            "duplicate_leads_delta_avoidance": "00:30:00",
            **data,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 201)
