"""
Test /activecampaign/ac_id
"""

from django.urls.base import reverse_lazy
from rest_framework import status

from breathecode.services import datetime_to_iso_format

from ..mixins import MarketingTestCase


class ActiveCampaignIdTestSuite(MarketingTestCase):
    """Test /activecampaign/ac_id"""

    """
    🔽🔽🔽 without Auth
    """

    def test_active_campaign_without_auth(self):
        """Test /activecampaign without auth"""
        url = reverse_lazy("marketing:activecampaign_id", kwargs={"ac_id": 1})
        data = {"ac_key": "88888", "ac_url": "https://www.tomatoes.com/"}
        response = self.client.put(url, data)
        json = response.json()
        expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    """
    🔽🔽🔽 without capability
    """

    def test_without_capability(self):
        """Test /activecampaign without data"""
        url = reverse_lazy("marketing:activecampaign_id", kwargs={"ac_id": 1})
        self.generate_models(
            authenticate=True,
            academy=True,
            profile_academy=True,
            active_campaign_academy=True,
            role="potato",
        )
        data = {"ac_key": "88888", "ac_url": "https://www.tomatoes.com/"}
        self.headers(academy=1)
        response = self.client.put(url, data)
        json = response.json()
        expected = {"detail": "You (user: 1) don't have this capability: crud_lead for academy 1", "status_code": 403}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    """
    🔽🔽🔽 Put With wrong active campaign Id
    """

    def test_without_data(self):
        """Test /activecampaign Put With wrong active campaign Id"""
        url = reverse_lazy("marketing:activecampaign_id", kwargs={"ac_id": 2})
        self.generate_models(
            authenticate=True,
            academy=True,
            profile_academy=True,
            capability="crud_lead",
            active_campaign_academy=True,
            role="potato",
        )
        self.headers(academy=1)
        data = {"ac_key": "55555555", "ac_url": "https://www.potato.com/"}
        response = self.client.put(url, data)
        json = response.json()
        expected = {"detail": "active-campaign-not-found", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    """
    🔽🔽🔽 Put without academy
    """

    def test_post_active_campaign_without_academy(self):
        """Test /activecampaign"""
        url = reverse_lazy("marketing:activecampaign_id", kwargs={"ac_id": 1})
        model = self.generate_models(
            authenticate=True,
            academy=True,
            profile_academy=True,
            active_campaign_academy=True,
            capability="crud_lead",
            role="potato",
        )
        data = {"ac_key": "55555555", "ac_url": "https://www.potato.com/"}
        response = self.client.put(url, data)
        json = response.json()

        expected = {
            "detail": "Missing academy_id parameter expected for the endpoint url or 'Academy' header",
            "status_code": 403,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    """
    🔽🔽🔽 Put
    """

    def test_put_active_campaign(self):
        """Test /activecampaign"""
        url = reverse_lazy("marketing:activecampaign_id", kwargs={"ac_id": 1})
        ac_kwargs = {"ac_key": "55555555", "ac_url": "https://www.potato.com/"}
        model = self.generate_models(
            authenticate=True,
            academy=True,
            profile_academy=True,
            active_campaign_academy=True,
            active_campaign_academy_kwargs=ac_kwargs,
            capability="crud_lead",
            role="potato",
        )
        self.headers(academy=1)
        data = {"ac_key": "88888", "ac_url": "https://www.tomatoes.com/"}
        response = self.client.put(url, data)
        json = response.json()

        self.assertDatetime(json["created_at"])
        self.assertDatetime(json["updated_at"])

        del json["created_at"]
        del json["updated_at"]

        expected = {
            "id": 1,
            "crm_vendor": "ACTIVE_CAMPAIGN",
            "event_attendancy_automation": None,
            "last_interaction_at": None,
            "sync_message": None,
            "sync_status": "INCOMPLETED",
            "duplicate_leads_delta_avoidance": "00:30:00",
            "crm_vendor": "ACTIVE_CAMPAIGN",
            **data,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)
