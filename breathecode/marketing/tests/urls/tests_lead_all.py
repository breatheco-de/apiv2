"""
Test /academy/lead
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


class CohortUserTestSuite(MarketingTestCase):
    """Test /academy/lead"""

    """
    🔽🔽🔽 Auth
    """

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_lead_all__without_auth(self):
        """Test /cohort/:id/user without auth"""
        url = reverse_lazy("marketing:lead_all")
        response = self.client.get(url)
        json = response.json()
        expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.all_form_entry_dict(), [])

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_lead_all__without_profile_acedemy(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        url = reverse_lazy("marketing:lead_all")
        model = self.generate_models(authenticate=True, form_entry=True)

        response = self.client.get(url)
        json = response.json()

        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_form_entry_dict(), [{**self.model_to_dict(model, "form_entry")}])

    """
    🔽🔽🔽 Without data
    """

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_lead_all__without_data(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        url = reverse_lazy("marketing:lead_all")
        model = self.generate_models(authenticate=True, profile_academy=True, capability="read_lead", role="potato")

        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_form_entry_dict(), [])

    """
    🔽🔽🔽 With data
    """

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_lead_all(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        url = reverse_lazy("marketing:lead_all")
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability="read_lead",
            role="potato",
            form_entry=True,
            form_entry_kwargs=generate_form_entry_kwargs(),
        )

        response = self.client.get(url)
        json = response.json()

        self.assertDatetime(json[0]["created_at"])
        del json[0]["created_at"]

        expected = [
            {
                "academy": {
                    "id": model.form_entry.academy.id,
                    "name": model.form_entry.academy.name,
                    "slug": model.form_entry.academy.slug,
                },
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
                "utm_source": model.form_entry.utm_source,
                "utm_url": model.form_entry.utm_url,
                "utm_placement": model.form_entry.utm_placement,
                "utm_term": model.form_entry.utm_term,
                "utm_plan": model.form_entry.utm_plan,
                "sex": model.form_entry.sex,
                "custom_fields": model.form_entry.custom_fields,
            }
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_form_entry_dict(), [{**self.model_to_dict(model, "form_entry")}])

    """
    🔽🔽🔽 Academy in querystring
    """

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_lead_all__with_bad_academy_in_querystring(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        url = reverse_lazy("marketing:lead_all") + "?academy=freyja"
        model = self.generate_models(
            authenticate=True, profile_academy=True, capability="read_lead", role="potato", form_entry=True
        )

        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_form_entry_dict(), [{**self.model_to_dict(model, "form_entry")}])

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_lead_all__with_academy_in_querystring(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        academy_kwargs = {"slug": "freyja"}
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability="read_lead",
            role="potato",
            form_entry=True,
            academy_kwargs=academy_kwargs,
        )

        url = reverse_lazy("marketing:lead_all") + "?academy=freyja"
        response = self.client.get(url)
        json = response.json()

        self.assertDatetime(json[0]["created_at"])
        del json[0]["created_at"]

        expected = [
            {
                "academy": {
                    "id": model.form_entry.academy.id,
                    "name": model.form_entry.academy.name,
                    "slug": model.form_entry.academy.slug,
                },
                "country": model.form_entry.country,
                "course": model.form_entry.course,
                "email": model.form_entry.email,
                "first_name": model.form_entry.first_name,
                "client_comments": model.form_entry.client_comments,
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
                "utm_source": model.form_entry.utm_source,
                "utm_url": model.form_entry.utm_url,
                "utm_placement": model.form_entry.utm_placement,
                "utm_term": model.form_entry.utm_term,
                "utm_plan": model.form_entry.utm_plan,
                "sex": model.form_entry.sex,
                "custom_fields": model.form_entry.custom_fields,
            }
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_form_entry_dict(), [{**self.model_to_dict(model, "form_entry")}])

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_lead_all__with_two_academy_in_querystring(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        base = self.generate_models(user=True)

        models = [
            self.generate_models(
                authenticate=True,
                profile_academy=True,
                capability="read_lead",
                role="potato",
                form_entry=True,
                models=base,
                academy_kwargs={"slug": "konan" if index == 0 else "freyja"},
            )
            for index in range(0, 2)
        ]

        models.sort(key=lambda x: x.form_entry.created_at)
        url = reverse_lazy("marketing:lead_all") + "?academy=" + ",".join([x.academy.slug for x in models])
        response = self.client.get(url)
        json = response.json()

        self.assertDatetime(json[0]["created_at"])
        del json[0]["created_at"]

        self.assertDatetime(json[1]["created_at"])
        del json[1]["created_at"]

        expected = [
            {
                "academy": {
                    "id": model.form_entry.academy.id,
                    "name": model.form_entry.academy.name,
                    "slug": model.form_entry.academy.slug,
                },
                "country": model.form_entry.country,
                "client_comments": model.form_entry.client_comments,
                "course": model.form_entry.course,
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
                "utm_source": model.form_entry.utm_source,
                "utm_url": model.form_entry.utm_url,
                "utm_placement": model.form_entry.utm_placement,
                "utm_term": model.form_entry.utm_term,
                "utm_plan": model.form_entry.utm_plan,
                "sex": model.form_entry.sex,
                "custom_fields": model.form_entry.custom_fields,
            }
            for model in models
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_form_entry_dict(), [{**self.model_to_dict(model, "form_entry")} for model in models])

    """
    🔽🔽🔽 Start in querystring
    """

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_lead_all__with_bad_start_in_querystring(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        url = reverse_lazy("marketing:lead_all") + "?start=2100-01-01"
        model = self.generate_models(
            authenticate=True, profile_academy=True, capability="read_lead", role="potato", form_entry=True
        )

        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_form_entry_dict(), [{**self.model_to_dict(model, "form_entry")}])

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_lead_all__with_start_in_querystring(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        query_date = (timezone.now() - timedelta(hours=48)).strftime("%Y-%m-%d")
        model = self.generate_models(
            authenticate=True, profile_academy=True, capability="read_lead", role="potato", form_entry=True
        )

        url = reverse_lazy("marketing:lead_all") + f"?start={query_date}"
        response = self.client.get(url)
        json = response.json()

        self.assertDatetime(json[0]["created_at"])
        del json[0]["created_at"]

        expected = [
            {
                "academy": {
                    "id": model.form_entry.academy.id,
                    "name": model.form_entry.academy.name,
                    "slug": model.form_entry.academy.slug,
                },
                "country": model.form_entry.country,
                "course": model.form_entry.course,
                "email": model.form_entry.email,
                "first_name": model.form_entry.first_name,
                "client_comments": model.form_entry.client_comments,
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
                "utm_source": model.form_entry.utm_source,
                "utm_url": model.form_entry.utm_url,
                "utm_placement": model.form_entry.utm_placement,
                "utm_term": model.form_entry.utm_term,
                "utm_plan": model.form_entry.utm_plan,
                "sex": model.form_entry.sex,
                "custom_fields": model.form_entry.custom_fields,
            }
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_form_entry_dict(), [{**self.model_to_dict(model, "form_entry")}])

    """
    🔽🔽🔽 End in querystring
    """

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_lead_all__with_bad_end_in_querystring(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        url = reverse_lazy("marketing:lead_all") + "?end=1900-01-01"
        model = self.generate_models(
            authenticate=True, profile_academy=True, capability="read_lead", role="potato", form_entry=True
        )

        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_form_entry_dict(), [{**self.model_to_dict(model, "form_entry")}])

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_lead_all__with_end_in_querystring(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        query_date = (timezone.now() + timedelta(hours=48)).strftime("%Y-%m-%d")
        model = self.generate_models(
            authenticate=True, profile_academy=True, capability="read_lead", role="potato", form_entry=True
        )

        url = reverse_lazy("marketing:lead_all") + f"?end={query_date}"
        response = self.client.get(url)
        json = response.json()

        self.assertDatetime(json[0]["created_at"])
        del json[0]["created_at"]

        expected = [
            {
                "academy": {
                    "id": model.form_entry.academy.id,
                    "name": model.form_entry.academy.name,
                    "slug": model.form_entry.academy.slug,
                },
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
                "utm_source": model.form_entry.utm_source,
                "utm_url": model.form_entry.utm_url,
                "utm_placement": model.form_entry.utm_placement,
                "utm_term": model.form_entry.utm_term,
                "utm_plan": model.form_entry.utm_plan,
                "sex": model.form_entry.sex,
                "custom_fields": model.form_entry.custom_fields,
            }
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_form_entry_dict(), [{**self.model_to_dict(model, "form_entry")}])
