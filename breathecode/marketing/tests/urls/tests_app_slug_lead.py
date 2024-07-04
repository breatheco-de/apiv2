"""
Test /academy/app_slug_lead
"""

from django.utils import timezone
from datetime import timedelta
import re, string
from random import choice, choices, randint
from mixer.main import Mixer
from unittest.mock import MagicMock, call, patch
from django.urls.base import reverse_lazy
from rest_framework import status
from faker import Faker
from breathecode.tests.mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_client_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_blob_mock,
)
from ..mixins import MarketingTestCase

fake = Faker()


def post_serializer(data={}):
    return {
        "attribution_id": None,
        "ac_contact_id": None,
        "ac_deal_id": None,
        "ac_expected_cohort": None,
        "academy": 1,
        "automations": "",
        "browser_lang": None,
        "city": None,
        "client_comments": None,
        "contact": None,
        "country": None,
        "course": None,
        "current_download": None,
        "deal_status": None,
        "email": None,
        "fb_ad_id": None,
        "fb_adgroup_id": None,
        "fb_form_id": None,
        "fb_leadgen_id": None,
        "fb_page_id": None,
        "first_name": "",
        "gclid": None,
        "id": 1,
        "last_name": "",
        "latitude": None,
        "lead_generation_app": 1,
        "lead_type": None,
        "location": None,
        "longitude": None,
        "phone": None,
        "referral_key": None,
        "sentiment": None,
        "state": None,
        "storage_status": "PENDING",
        "street_address": None,
        "tags": "",
        "user": None,
        "utm_campaign": None,
        "utm_medium": None,
        "utm_source": None,
        "utm_content": None,
        "utm_placement": None,
        "utm_term": None,
        "utm_plan": None,
        "sex": None,
        "custom_fields": None,
        "won_at": None,
        "zip_code": None,
        "utm_url": None,
        "storage_status_text": "",
        "ac_deal_owner_full_name": None,
        "ac_deal_course": None,
        "ac_deal_location": None,
        "ac_deal_owner_id": None,
        "ac_expected_cohort_date": None,
        "ac_deal_amount": None,
        "ac_deal_currency_code": None,
        **data,
    }


def form_entry_field(data={}):
    return {
        "id": 1,
        "attribution_id": None,
        "ac_contact_id": None,
        "ac_deal_id": None,
        "ac_expected_cohort": None,
        "academy_id": 1,
        "automations": "",
        "browser_lang": None,
        "city": None,
        "client_comments": None,
        "contact_id": None,
        "country": None,
        "course": None,
        "current_download": None,
        "deal_status": None,
        "email": None,
        "fb_ad_id": None,
        "fb_adgroup_id": None,
        "fb_form_id": None,
        "fb_leadgen_id": None,
        "fb_page_id": None,
        "first_name": "",
        "gclid": None,
        "id": 1,
        "last_name": "",
        "latitude": None,
        "lead_generation_app_id": 1,
        "lead_type": None,
        "location": None,
        "longitude": None,
        "phone": None,
        "referral_key": None,
        "sentiment": None,
        "state": None,
        "storage_status": "PENDING",
        "storage_status_text": "",
        "street_address": None,
        "tags": "",
        "user_id": None,
        "utm_campaign": None,
        "utm_medium": None,
        "utm_content": None,
        "utm_source": None,
        "utm_placement": None,
        "utm_term": None,
        "utm_plan": None,
        "utm_url": None,
        "sex": None,
        "custom_fields": None,
        "won_at": None,
        "zip_code": None,
        "ac_deal_course": None,
        "ac_deal_location": None,
        "ac_deal_owner_full_name": None,
        "ac_deal_owner_id": None,
        "ac_expected_cohort_date": None,
        "ac_deal_amount": None,
        "ac_deal_currency_code": None,
        **data,
    }


class FakeRecaptcha:

    class RiskAnalysis:

        def __init__(self, *args, **kwargs):
            self.score = 0.9

    def __init__(self, *args, **kwargs):
        self.risk_analysis = self.RiskAnalysis()


class AppSlugLeadTestSuite(MarketingTestCase):
    """
    🔽🔽🔽 Post without app slug or app_id
    """

    @patch("breathecode.marketing.tasks.persist_single_lead", MagicMock())
    @patch.multiple(
        "breathecode.services.google_cloud.Recaptcha",
        __init__=MagicMock(return_value=None),
        create_assessment=MagicMock(return_value=FakeRecaptcha()),
    )
    def test_app_slug_lead__post__without_app_slug_or_app_id(self):
        from breathecode.marketing.tasks import persist_single_lead

        url = reverse_lazy("marketing:app_slug_lead", kwargs={"app_slug": "they-killed-kenny"})
        response = self.client.post(url)

        json = response.json()
        expected = {"detail": "without-app-slug-or-app-id", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_lead_generation_app_dict(), [])

        self.assertEqual(persist_single_lead.delay.call_args_list, [])

    """
    🔽🔽🔽 Post without app_id
    """

    @patch("breathecode.marketing.tasks.persist_single_lead", MagicMock())
    @patch.multiple(
        "breathecode.services.google_cloud.Recaptcha",
        __init__=MagicMock(return_value=None),
        create_assessment=MagicMock(return_value=FakeRecaptcha()),
    )
    def test_app_slug_lead__post__without_app_id(self):
        from breathecode.marketing.tasks import persist_single_lead

        model = self.generate_models(lead_generation_app=True)

        url = (
            reverse_lazy("marketing:app_slug_lead", kwargs={"app_slug": "they-killed-kenny"})
            + f"?app_id={model.lead_generation_app.app_id}"
        )
        response = self.client.post(url)

        json = response.json()
        expected = {"detail": "without-app-id", "status_code": 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.all_lead_generation_app_dict(), [self.model_to_dict(model, "lead_generation_app")])

        self.assertEqual(persist_single_lead.delay.call_args_list, [])

    """
    🔽🔽🔽 Post without required fields
    """

    @patch("breathecode.marketing.tasks.persist_single_lead", MagicMock())
    @patch.multiple(
        "breathecode.services.google_cloud.Recaptcha",
        __init__=MagicMock(return_value=None),
        create_assessment=MagicMock(return_value=FakeRecaptcha()),
    )
    def test_app_slug_lead__post__without_required_fields(self):
        from breathecode.marketing.tasks import persist_single_lead

        model = self.generate_models(lead_generation_app=True)

        url = (
            reverse_lazy("marketing:app_slug_lead", kwargs={"app_slug": model.lead_generation_app.slug})
            + f"?app_id={model.lead_generation_app.app_id}"
        )

        start = timezone.now()
        response = self.client.post(url)
        end = timezone.now()

        json = response.json()
        expected = {"language": ["This field may not be null."]}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        db = self.all_lead_generation_app_dict()
        last_call_at = db[0]["last_call_at"]

        self.assertGreater(end, last_call_at)
        self.assertGreater(last_call_at, start)

        db[0]["last_call_at"] = None

        self.assertEqual(
            db,
            [
                {
                    **self.model_to_dict(model, "lead_generation_app"),
                    "last_call_log": '{"language": ["This field may not be null."]}',
                    "hits": 1,
                    "last_call_status": "ERROR",
                    "last_request_data": "{}",
                    "last_call_log": '{"language": ["This field may not be null."]}',
                }
            ],
        )

        self.assertEqual(persist_single_lead.delay.call_args_list, [])

    """
    🔽🔽🔽 Post data
    """

    @patch("breathecode.marketing.tasks.persist_single_lead", MagicMock())
    @patch.multiple(
        "breathecode.services.google_cloud.Recaptcha",
        __init__=MagicMock(return_value=None),
        create_assessment=MagicMock(return_value=FakeRecaptcha()),
    )
    def test_app_slug_lead__post(self):
        from breathecode.marketing.tasks import persist_single_lead

        model = self.generate_models(lead_generation_app=True)

        url = (
            reverse_lazy("marketing:app_slug_lead", kwargs={"app_slug": model.lead_generation_app.slug})
            + f"?app_id={model.lead_generation_app.app_id}"
        )
        data = {"language": "eo"}

        start = timezone.now()
        response = self.client.post(url, data, format="json")
        end = timezone.now()

        json = response.json()

        created_at_iso_string = json["created_at"]
        updated_at_iso_string = json["updated_at"]
        created_at = self.iso_to_datetime(created_at_iso_string)
        updated_at = self.iso_to_datetime(updated_at_iso_string)

        self.assertGreater(end, created_at)
        self.assertGreater(created_at, start)

        self.assertGreater(end, updated_at)
        self.assertGreater(updated_at, start)

        del json["created_at"]
        del json["updated_at"]

        expected = post_serializer(
            {
                **data,
            }
        )

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        form_entry = form_entry_field(
            {
                **data,
            }
        )
        self.assertEqual(self.all_form_entry_dict(), [form_entry])

        db = self.all_lead_generation_app_dict()
        last_call_at = db[0]["last_call_at"]

        self.assertGreater(end, last_call_at)
        self.assertGreater(last_call_at, start)

        db[0]["last_call_at"] = None

        self.assertEqual(
            db,
            [
                {
                    **self.model_to_dict(model, "lead_generation_app"),
                    "hits": 1,
                    "last_call_status": "OK",
                    "last_request_data": '{"language": "eo"}',
                }
            ],
        )

        form_entry["academy"] = 1
        form_entry["contact"] = None
        form_entry["created_at"] = created_at_iso_string
        form_entry["updated_at"] = updated_at_iso_string
        form_entry["contact"] = None
        form_entry["lead_generation_app"] = 1
        form_entry["user"] = None

        del form_entry["academy_id"]
        del form_entry["contact_id"]
        del form_entry["lead_generation_app_id"]
        del form_entry["user_id"]

        self.assertEqual(persist_single_lead.delay.call_args_list, [call(form_entry)])

    """
    🔽🔽🔽 Post data with bad utm_url (this resolve a bug)
    """

    @patch("breathecode.marketing.tasks.persist_single_lead", MagicMock())
    @patch.multiple(
        "breathecode.services.google_cloud.Recaptcha",
        __init__=MagicMock(return_value=None),
        create_assessment=MagicMock(return_value=FakeRecaptcha()),
    )
    def test_app_slug_lead__post__with_utm_url(self):
        from breathecode.marketing.tasks import persist_single_lead

        model = self.generate_models(lead_generation_app=True)

        url = (
            reverse_lazy("marketing:app_slug_lead", kwargs={"app_slug": model.lead_generation_app.slug})
            + f"?app_id={model.lead_generation_app.app_id}"
        )
        data = {"language": "eo", "utm_url": "https:/bad_url/google.co.ve/"}

        start = timezone.now()
        response = self.client.post(url, data, format="json")
        end = timezone.now()

        json = response.json()

        created_at_iso_string = json["created_at"]
        updated_at_iso_string = json["updated_at"]
        created_at = self.iso_to_datetime(created_at_iso_string)
        updated_at = self.iso_to_datetime(updated_at_iso_string)

        self.assertGreater(end, created_at)
        self.assertGreater(created_at, start)

        self.assertGreater(end, updated_at)
        self.assertGreater(updated_at, start)

        del json["created_at"]
        del json["updated_at"]

        expected = {
            "attribution_id": None,
            "ac_contact_id": None,
            "ac_deal_id": None,
            "ac_expected_cohort": None,
            "academy": 1,
            "automations": "",
            "browser_lang": None,
            "city": None,
            "client_comments": None,
            "contact": None,
            "country": None,
            "course": None,
            "current_download": None,
            "deal_status": None,
            "email": None,
            "fb_ad_id": None,
            "fb_adgroup_id": None,
            "fb_form_id": None,
            "fb_leadgen_id": None,
            "fb_page_id": None,
            "first_name": "",
            "gclid": None,
            "id": 1,
            "last_name": "",
            "latitude": None,
            "lead_generation_app": 1,
            "lead_type": None,
            "location": None,
            "longitude": None,
            "phone": None,
            "referral_key": None,
            "sentiment": None,
            "state": None,
            "storage_status": "PENDING",
            "storage_status_text": "",
            "street_address": None,
            "tags": "",
            "user": None,
            "utm_campaign": None,
            "utm_medium": None,
            "utm_content": None,
            "utm_source": None,
            "utm_placement": None,
            "utm_term": None,
            "utm_plan": None,
            "sex": None,
            "custom_fields": None,
            "won_at": None,
            "zip_code": None,
            "ac_deal_course": None,
            "ac_deal_location": None,
            "ac_deal_owner_full_name": None,
            "ac_deal_owner_id": None,
            "ac_expected_cohort_date": None,
            "ac_deal_amount": None,
            "ac_deal_currency_code": None,
            **data,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        form_entry = form_entry_field(
            {
                **data,
            }
        )
        self.assertEqual(self.all_form_entry_dict(), [form_entry])

        db = self.all_lead_generation_app_dict()
        last_call_at = db[0]["last_call_at"]

        self.assertGreater(end, last_call_at)
        self.assertGreater(last_call_at, start)

        db[0]["last_call_at"] = None

        self.assertEqual(
            db,
            [
                {
                    **self.model_to_dict(model, "lead_generation_app"),
                    "hits": 1,
                    "last_call_status": "OK",
                    "last_request_data": '{"language": "eo", "utm_url": "https:/bad_url/google.co.ve/"}',
                }
            ],
        )

        form_entry["academy"] = 1
        form_entry["contact"] = None
        form_entry["created_at"] = created_at_iso_string
        form_entry["updated_at"] = updated_at_iso_string
        form_entry["contact"] = None
        form_entry["lead_generation_app"] = 1
        form_entry["user"] = None

        del form_entry["academy_id"]
        del form_entry["contact_id"]
        del form_entry["lead_generation_app_id"]
        del form_entry["user_id"]

        self.assertEqual(persist_single_lead.delay.call_args_list, [call(form_entry)])

    """
    🔽🔽🔽 Post data with automations
    """

    @patch("breathecode.marketing.tasks.persist_single_lead", MagicMock())
    @patch.multiple(
        "breathecode.services.google_cloud.Recaptcha",
        __init__=MagicMock(return_value=None),
        create_assessment=MagicMock(return_value=FakeRecaptcha()),
    )
    def test_app_slug_lead__post__with_automations(self):
        from breathecode.marketing.tasks import persist_single_lead

        model = self.generate_models(lead_generation_app=True)

        url = (
            reverse_lazy("marketing:app_slug_lead", kwargs={"app_slug": model.lead_generation_app.slug})
            + f"?app_id={model.lead_generation_app.app_id}"
        )
        data = {"language": "eo", "automations": "they-killed-kenny1,they-killed-kenny2"}

        start = timezone.now()
        response = self.client.post(url, data, format="json")
        end = timezone.now()

        json = response.json()

        created_at_iso_string = json["created_at"]
        updated_at_iso_string = json["updated_at"]
        created_at = self.iso_to_datetime(created_at_iso_string)
        updated_at = self.iso_to_datetime(updated_at_iso_string)

        self.assertGreater(end, created_at)
        self.assertGreater(created_at, start)

        self.assertGreater(end, updated_at)
        self.assertGreater(updated_at, start)

        del json["created_at"]
        del json["updated_at"]

        expected = post_serializer(
            {
                **data,
            }
        )

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        form_entry = form_entry_field(
            {
                **data,
            }
        )
        self.assertEqual(self.all_form_entry_dict(), [form_entry])

        db = self.all_lead_generation_app_dict()
        last_call_at = db[0]["last_call_at"]

        self.assertGreater(end, last_call_at)
        self.assertGreater(last_call_at, start)

        db[0]["last_call_at"] = None

        self.assertEqual(
            db,
            [
                {
                    **self.model_to_dict(model, "lead_generation_app"),
                    "hits": 1,
                    "last_call_status": "OK",
                    "last_request_data": '{"language": "eo", "automations": "they-killed-kenny1,they-killed-kenny2"}',
                }
            ],
        )

        form_entry["academy"] = 1
        form_entry["contact"] = None
        form_entry["created_at"] = created_at_iso_string
        form_entry["updated_at"] = updated_at_iso_string
        form_entry["contact"] = None
        form_entry["lead_generation_app"] = 1
        form_entry["user"] = None

        del form_entry["academy_id"]
        del form_entry["contact_id"]
        del form_entry["lead_generation_app_id"]
        del form_entry["user_id"]

        self.assertEqual(persist_single_lead.delay.call_args_list, [call(form_entry)])

    """
    🔽🔽🔽 Post data with tags
    """

    @patch("breathecode.marketing.tasks.persist_single_lead", MagicMock())
    @patch.multiple(
        "breathecode.services.google_cloud.Recaptcha",
        __init__=MagicMock(return_value=None),
        create_assessment=MagicMock(return_value=FakeRecaptcha()),
    )
    def test_app_slug_lead__post__with_tags(self):
        from breathecode.marketing.tasks import persist_single_lead

        model = self.generate_models(lead_generation_app=True)

        url = (
            reverse_lazy("marketing:app_slug_lead", kwargs={"app_slug": model.lead_generation_app.slug})
            + f"?app_id={model.lead_generation_app.app_id}"
        )
        data = {"language": "eo", "tags": "they-killed-kenny1,they-killed-kenny2"}

        start = timezone.now()
        response = self.client.post(url, data, format="json")
        end = timezone.now()

        json = response.json()

        created_at_iso_string = json["created_at"]
        updated_at_iso_string = json["updated_at"]
        created_at = self.iso_to_datetime(created_at_iso_string)
        updated_at = self.iso_to_datetime(updated_at_iso_string)

        self.assertGreater(end, created_at)
        self.assertGreater(created_at, start)

        self.assertGreater(end, updated_at)
        self.assertGreater(updated_at, start)

        del json["created_at"]
        del json["updated_at"]

        expected = {
            "attribution_id": None,
            "ac_contact_id": None,
            "ac_deal_id": None,
            "ac_expected_cohort": None,
            "academy": 1,
            "automations": "",
            "browser_lang": None,
            "city": None,
            "client_comments": None,
            "contact": None,
            "country": None,
            "course": None,
            "current_download": None,
            "deal_status": None,
            "email": None,
            "fb_ad_id": None,
            "fb_adgroup_id": None,
            "fb_form_id": None,
            "fb_leadgen_id": None,
            "fb_page_id": None,
            "first_name": "",
            "gclid": None,
            "id": 1,
            "last_name": "",
            "latitude": None,
            "lead_generation_app": 1,
            "lead_type": None,
            "location": None,
            "longitude": None,
            "phone": None,
            "referral_key": None,
            "sentiment": None,
            "state": None,
            "storage_status": "PENDING",
            "storage_status_text": "",
            "street_address": None,
            "tags": "",
            "user": None,
            "utm_campaign": None,
            "utm_medium": None,
            "utm_content": None,
            "utm_source": None,
            "utm_placement": None,
            "utm_term": None,
            "utm_plan": None,
            "sex": None,
            "custom_fields": None,
            "won_at": None,
            "zip_code": None,
            "utm_url": None,
            "ac_deal_course": None,
            "ac_deal_location": None,
            "ac_deal_owner_full_name": None,
            "ac_deal_owner_id": None,
            "ac_expected_cohort_date": None,
            "ac_deal_amount": None,
            "ac_deal_currency_code": None,
            **data,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        form_entry = form_entry_field(
            {
                **data,
            }
        )
        self.assertEqual(self.all_form_entry_dict(), [form_entry])

        db = self.all_lead_generation_app_dict()
        last_call_at = db[0]["last_call_at"]

        self.assertGreater(end, last_call_at)
        self.assertGreater(last_call_at, start)

        db[0]["last_call_at"] = None

        self.assertEqual(
            db,
            [
                {
                    **self.model_to_dict(model, "lead_generation_app"),
                    "hits": 1,
                    "last_call_status": "OK",
                    "last_request_data": '{"language": "eo", "tags": "they-killed-kenny1,they-killed-kenny2"}',
                }
            ],
        )

        form_entry["academy"] = 1
        form_entry["contact"] = None
        form_entry["created_at"] = created_at_iso_string
        form_entry["updated_at"] = updated_at_iso_string
        form_entry["contact"] = None
        form_entry["lead_generation_app"] = 1
        form_entry["user"] = None

        del form_entry["academy_id"]
        del form_entry["contact_id"]
        del form_entry["lead_generation_app_id"]
        del form_entry["user_id"]

        self.assertEqual(persist_single_lead.delay.call_args_list, [call(form_entry)])
