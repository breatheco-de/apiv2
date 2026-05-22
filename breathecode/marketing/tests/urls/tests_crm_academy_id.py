"""
Test /crmacademy/<crm_academy_id>
"""

from django.urls.base import reverse_lazy
from rest_framework import status

from ..mixins import MarketingTestCase


class CrmAcademyIdTestSuite(MarketingTestCase):
    """Test /crmacademy/<crm_academy_id>"""

    def test_crm_academy_without_auth(self):
        """Test PUT /crmacademy without auth"""
        url = reverse_lazy("marketing:crm_academy_id", kwargs={"crm_academy_id": 1})
        data = {"ac_key": "88888", "ac_url": "https://www.tomatoes.com/"}
        response = self.client.put(url, data)
        json = response.json()
        expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_without_capability(self):
        """Test PUT /crmacademy without capability"""
        url = reverse_lazy("marketing:crm_academy_id", kwargs={"crm_academy_id": 1})
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

    def test_without_data(self):
        """Test PUT /crmacademy with wrong CRM academy id"""
        url = reverse_lazy("marketing:crm_academy_id", kwargs={"crm_academy_id": 2})
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

    def test_put_crm_academy_without_academy(self):
        """Test PUT /crmacademy without academy header"""
        url = reverse_lazy("marketing:crm_academy_id", kwargs={"crm_academy_id": 1})
        self.generate_models(
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

    def test_put_crm_academy(self):
        """Test PUT /crmacademy"""
        url = reverse_lazy("marketing:crm_academy_id", kwargs={"crm_academy_id": 1})
        ac_kwargs = {"ac_key": "55555555", "ac_url": "https://www.potato.com/"}
        self.generate_models(
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
            "status_page_url": None,
            **data,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)

    def test_put_crm_academy_with_status_page_url(self):
        """Test PUT /crmacademy with status_page_url"""
        url = reverse_lazy("marketing:crm_academy_id", kwargs={"crm_academy_id": 1})
        ac_kwargs = {"ac_key": "55555555", "ac_url": "https://www.potato.com/"}
        self.generate_models(
            authenticate=True,
            academy=True,
            profile_academy=True,
            active_campaign_academy=True,
            active_campaign_academy_kwargs=ac_kwargs,
            capability="crud_lead",
            role="potato",
        )
        self.headers(academy=1)
        data = {
            "ac_key": "88888",
            "ac_url": "https://www.tomatoes.com/",
            "status_page_url": "https://status.activecampaign.com/",
        }
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
            **data,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)

    def test_put_crm_academy_deprecated_alias(self):
        """Test PUT /activecampaign deprecated alias"""
        url = reverse_lazy("marketing:activecampaign_id", kwargs={"crm_academy_id": 1})
        ac_kwargs = {"ac_key": "55555555", "ac_url": "https://www.potato.com/"}
        self.generate_models(
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
            "status_page_url": None,
            **data,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)
