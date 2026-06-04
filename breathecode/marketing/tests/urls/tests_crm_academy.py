"""
Test /crmacademy
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
        "status_page_url": active_campaign_academy.status_page_url,
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


class CrmAcademyTestSuite(MarketingTestCase):
    """Test /crmacademy"""

    def test_crm_academy_without_auth(self):
        """Test /crmacademy without auth"""
        url = reverse_lazy("marketing:crm_academy")
        response = self.client.get(url)
        json = response.json()
        expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.all_active_campaign_academy_dict(), [])

    def test_without_capability(self):
        """Test /crmacademy without capability"""
        url = reverse_lazy("marketing:crm_academy")
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

    def test_without_academy_header(self):
        """Test /crmacademy without academy header"""
        url = reverse_lazy("marketing:crm_academy")
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

    def test_without_data(self):
        """Test /crmacademy without CRM academy record"""
        url = reverse_lazy("marketing:crm_academy")
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
        expected = {"detail": "CRM academy not found", "status_code": 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.all_active_campaign_academy_dict(), [])

    def test_crm_academy(self):
        """Test GET /crmacademy"""
        url = reverse_lazy("marketing:crm_academy")
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

    def test_crm_academy_deprecated_alias(self):
        """Test GET /activecampaign deprecated alias"""
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

    def test_post_crm_academy_without_academy(self):
        """Test POST /crmacademy without academy header"""
        url = reverse_lazy("marketing:crm_academy")
        self.generate_models(
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

    def test_post_crm_academy(self):
        """Test POST /crmacademy"""
        url = reverse_lazy("marketing:crm_academy")
        self.generate_models(
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
        self.assertEqual(response.status_code, 201)
