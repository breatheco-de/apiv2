"""
Test /academy/lead/id
"""

from django.utils import timezone
from datetime import timedelta
import re, string
from random import choice, choices, randint
from mixer.main import Mixer
from unittest.mock import patch
from django.urls.base import reverse_lazy
from rest_framework import status
from breathecode.tests.mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_client_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_blob_mock,
)
from ..mixins import MarketingTestCase


def random_string():
    return "".join(choices(string.ascii_letters, k=10))


def generate_form_entry_kwargs():
    """That random values is too long that i prefer have it in one function"""
    return {
        "fb_leadgen_id": randint(0, 9999),
        "fb_page_id": randint(0, 9999),
        "fb_form_id": randint(0, 9999),
        "fb_adgroup_id": randint(0, 9999),
        "fb_ad_id": randint(0, 9999),
        "gclid": random_string(),
        "first_name": choice(["Rene", "Albert", "Immanuel"]),
        "last_name": choice(["Descartes", "Camus", "Kant"]),
        "email": choice(["a@a.com", "b@b.com", "c@c.com"]),
        "phone": choice(["123", "456", "789"]),
        "course": random_string(),
        "client_comments": random_string(),
        "location": random_string(),
        "language": random_string(),
        "utm_url": random_string(),
        "utm_medium": random_string(),
        "utm_campaign": random_string(),
        "utm_source": random_string(),
        "referral_key": random_string(),
        "gclid": random_string(),
        "tags": random_string(),
        "automations": random_string(),
        "street_address": random_string(),
        "country": random_string(),
        "city": random_string(),
        "latitude": randint(0, 9999),
        "longitude": randint(0, 9999),
        "state": random_string(),
        "zip_code": str(randint(0, 9999)),
        "browser_lang": random_string(),
        "storage_status": choice(["PENDING", "PERSISTED"]),
        "lead_type": choice(["STRONG", "SOFT", "DISCOVERY"]),
        "deal_status": choice(["WON", "LOST"]),
        "sentiment": choice(["GOOD", "BAD"]),
    }


class CohortLeadIdSuite(MarketingTestCase):
    """Test /academy/lead"""

    """
    🔽🔽🔽 No auth
    """

    def test_lead_id_no_auth(self):
        self.headers(academy=1)
        url = reverse_lazy("marketing:academy_lead_id", kwargs={"lead_id": 1})

        response = self.client.get(url)
        json = response.json()
        expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 401)

    """
    🔽🔽🔽 No credentials
    """

    def test_lead_id_without_capability(self):
        self.headers(academy=1)
        url = reverse_lazy("marketing:academy_lead_id", kwargs={"lead_id": 1})
        self.generate_models(authenticate=True)

        response = self.client.get(url)
        json = response.json()
        expected = {"detail": "You (user: 1) don't have this capability: read_lead for academy 1", "status_code": 403}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 403)

    """
    🔽🔽🔽 Single lead with data wrong id
    """

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_lead_wrong_id(self):
        """Test /lead/:id/ with data wrong id"""
        self.headers(academy=1)
        url = reverse_lazy("marketing:academy_lead_id", kwargs={"lead_id": 1})
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability="read_lead",
            role="potato",
        )

        response = self.client.get(url)
        json = response.json()

        expected = {"detail": "lead-not-found", "status_code": 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 404)

    """
    🔽🔽🔽 Single lead with data
    """

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_single_lead(self):
        """Test /lead/:id/ with data"""
        self.headers(academy=1)
        url = reverse_lazy("marketing:academy_lead_id", kwargs={"lead_id": 1})
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability="read_lead",
            role="potato",
            form_entry=2,
        )

        response = self.client.get(url)
        json = response.json()

        self.assertDatetime(json["created_at"])
        del json["created_at"]

        expected = {
            "ac_expected_cohort": model.form_entry[0].ac_expected_cohort,
            "automation_objects": [],
            "tag_objects": [],
            "automations": model.form_entry[0].automations,
            "browser_lang": model.form_entry[0].browser_lang,
            "city": model.form_entry[0].city,
            "country": model.form_entry[0].country,
            "course": model.form_entry[0].course,
            "client_comments": model.form_entry[0].client_comments,
            "email": model.form_entry[0].email,
            "first_name": model.form_entry[0].first_name,
            "gclid": model.form_entry[0].gclid,
            "id": model.form_entry[0].id,
            "language": model.form_entry[0].language,
            "last_name": model.form_entry[0].last_name,
            "lead_type": model.form_entry[0].lead_type,
            "location": model.form_entry[0].location,
            "storage_status": model.form_entry[0].storage_status,
            "tags": model.form_entry[0].tags,
            "utm_campaign": model.form_entry[0].utm_campaign,
            "utm_medium": model.form_entry[0].utm_medium,
            "utm_content": model.form_entry[0].utm_content,
            "utm_source": model.form_entry[0].utm_source,
            "utm_url": model.form_entry[0].utm_url,
            "utm_placement": model.form_entry[0].utm_placement,
            "utm_term": model.form_entry[0].utm_term,
            "utm_plan": model.form_entry[0].utm_plan,
            "custom_fields": model.form_entry[0].custom_fields,
            "sex": model.form_entry[0].sex,
            "latitude": model.form_entry[0].latitude,
            "longitude": model.form_entry[0].longitude,
            "phone": model.form_entry[0].phone,
            "user": model.form_entry[0].user,
            "referral_key": model.form_entry[0].referral_key,
            "state": model.form_entry[0].state,
            "storage_status_text": model.form_entry[0].storage_status_text,
            "street_address": model.form_entry[0].street_address,
            "won_at": model.form_entry[0].won_at,
            "updated_at": self.bc.datetime.to_iso_string(model.form_entry[0].updated_at),
            "lead_generation_app": model.form_entry[0].lead_generation_app,
            "fb_page_id": model.form_entry[0].fb_page_id,
            "fb_leadgen_id": model.form_entry[0].fb_leadgen_id,
            "fb_form_id": model.form_entry[0].fb_form_id,
            "fb_adgroup_id": model.form_entry[0].fb_adgroup_id,
            "fb_ad_id": model.form_entry[0].fb_ad_id,
            "deal_status": model.form_entry[0].deal_status,
            "current_download": model.form_entry[0].current_download,
            "contact": model.form_entry[0].contact,
            "ac_deal_id": model.form_entry[0].ac_deal_id,
            "ac_contact_id": model.form_entry[0].ac_contact_id,
            "sentiment": model.form_entry[0].sentiment,
            "ac_expected_cohort_date": model.form_entry[0].ac_expected_cohort_date,
            "ac_deal_location": model.form_entry[0].ac_deal_location,
            "ac_deal_course": model.form_entry[0].ac_deal_course,
            "ac_deal_owner_id": model.form_entry[0].ac_deal_owner_id,
            "ac_deal_owner_full_name": model.form_entry[0].ac_deal_owner_full_name,
            "academy": {
                "id": model.form_entry[0].academy.id,
                "name": model.form_entry[0].academy.name,
                "slug": model.form_entry[0].academy.slug,
            },
            "zip_code": model.form_entry[0].zip_code,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    """
    🔽🔽🔽 Update lead with wrong id
    """

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_update_lead_wrong_id(self):
        """Test /lead/:id/ with data wrong id"""
        self.headers(academy=1)
        url = reverse_lazy("marketing:academy_lead_id", kwargs={"lead_id": 1})
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability="crud_lead",
            role="potato",
        )

        data = {"first_name": "Juan"}
        response = self.client.put(url, data, format="json")
        json = response.json()

        expected = {"detail": "lead-not-found", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 400)

    """
    🔽🔽🔽 Update lead
    """

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_update_lead(self):
        """Test /lead/:id/ with data wrong id"""
        self.headers(academy=1)
        url = reverse_lazy("marketing:academy_lead_id", kwargs={"lead_id": 1})
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability="crud_lead",
            role="potato",
            form_entry=True,
        )

        data = {
            "id": 1,
            "first_name": self.bc.fake.first_name(),
            "last_name": self.bc.fake.last_name(),
            "email": self.bc.fake.email(),
            "utm_url": self.bc.fake.url(),
            "utm_medium": self.bc.fake.slug(),
            "utm_campaign": self.bc.fake.slug(),
            "utm_source": self.bc.fake.slug(),
            "gclid": random_string(),
        }
        response = self.client.put(url, data, format="json")
        json = response.json()

        self.assertDatetime(json["created_at"])
        del json["created_at"]
        self.assertDatetime(json["updated_at"])
        del json["updated_at"]
        del json["custom_fields"]

        expected = {
            "ac_contact_id": model.form_entry.ac_contact_id,
            "ac_deal_id": model.form_entry.ac_deal_id,
            "ac_expected_cohort": model.form_entry.ac_expected_cohort,
            "academy": {
                "id": model.form_entry.academy.id,
                "name": model.form_entry.academy.name,
                "slug": model.form_entry.academy.slug,
            },
            "automation_objects": [],
            "tag_objects": [],
            "automations": model.form_entry.automations,
            "fb_ad_id": model.form_entry.fb_ad_id,
            "fb_adgroup_id": model.form_entry.fb_adgroup_id,
            "fb_form_id": model.form_entry.fb_form_id,
            "fb_leadgen_id": model.form_entry.fb_leadgen_id,
            "fb_page_id": model.form_entry.fb_page_id,
            "current_download": model.form_entry.current_download,
            "contact": model.form_entry.contact,
            "deal_status": model.form_entry.deal_status,
            "browser_lang": model.form_entry.browser_lang,
            "city": model.form_entry.city,
            "country": model.form_entry.country,
            "course": model.form_entry.course,
            "client_comments": model.form_entry.client_comments,
            "email": model.form_entry.email,
            "first_name": model.form_entry.first_name,
            "gclid": model.form_entry.gclid,
            "id": model.form_entry.id,
            "language": model.form_entry.language,
            "last_name": model.form_entry.last_name,
            "lead_type": model.form_entry.lead_type,
            "location": model.form_entry.location,
            "storage_status": model.form_entry.storage_status,
            "tags": model.form_entry.tags,
            "utm_campaign": model.form_entry.utm_campaign,
            "utm_medium": model.form_entry.utm_medium,
            "utm_content": model.form_entry.utm_content,
            "utm_source": model.form_entry.utm_source,
            "utm_placement": model.form_entry.utm_placement,
            "utm_term": model.form_entry.utm_term,
            "utm_plan": model.form_entry.utm_plan,
            "sex": model.form_entry.sex,
            "utm_url": model.form_entry.utm_url,
            "latitude": model.form_entry.latitude,
            "longitude": model.form_entry.longitude,
            "phone": model.form_entry.phone,
            "user": model.form_entry.user,
            "referral_key": model.form_entry.referral_key,
            "state": model.form_entry.state,
            "storage_status_text": model.form_entry.storage_status_text,
            "street_address": model.form_entry.street_address,
            "won_at": model.form_entry.won_at,
            "zip_code": model.form_entry.zip_code,
            "sentiment": model.form_entry.sentiment,
            "lead_generation_app": model.form_entry.ac_deal_location,
            "ac_deal_location": model.form_entry.ac_deal_owner_full_name,
            "ac_deal_course": model.form_entry.ac_deal_course,
            "ac_deal_owner_full_name": model.form_entry.ac_deal_owner_full_name,
            "ac_deal_owner_id": model.form_entry.ac_deal_owner_id,
            "ac_expected_cohort_date": model.form_entry.ac_expected_cohort_date,
            **data,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
