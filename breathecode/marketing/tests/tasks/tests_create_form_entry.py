"""
Test /answer/:id
"""

from django.utils import timezone
from breathecode.marketing.tasks import create_form_entry
from breathecode.marketing import tasks
import re, string, os
import logging
from datetime import datetime
from unittest.mock import PropertyMock, patch, MagicMock, call
from django.urls.base import reverse_lazy
from rest_framework import status
from breathecode.services.datetime_to_iso_format import datetime_to_iso_format
from random import choice, choices, randint
from breathecode.tests.mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_client_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_blob_mock,
    MAILGUN_PATH,
    MAILGUN_INSTANCES,
    apply_mailgun_requests_post_mock,
    OLD_BREATHECODE_PATH,
    OLD_BREATHECODE_INSTANCES,
    apply_old_breathecode_requests_request_mock,
    REQUESTS_PATH,
    apply_requests_get_mock,
)
from ..mixins import MarketingTestCase
from faker import Faker

GOOGLE_CLOUD_KEY = os.getenv("GOOGLE_CLOUD_KEY", None)

fake = Faker()
fake_url = fake.url()

UTC_NOW = timezone.now()


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
        "phone": "123456789",
        "course": random_string(),
        "client_comments": random_string(),
        "location": random_string(),
        "language": "en",
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
        "latitude": 15,
        "longitude": 15,
        "state": random_string(),
        "zip_code": randint(0, 9999),
        "browser_lang": random_string(),
        "storage_status": choice(["PENDING", "PERSISTED"]),
        "lead_type": choice(["STRONG", "SOFT", "DISCOVERY"]),
        "deal_status": choice(["WON", "LOST"]),
        "sentiment": choice(["GOOD", "BAD"]),
        "current_download": fake_url,
    }


def form_entry_field(data={}):
    return {
        "id": 1,
        "fb_leadgen_id": None,
        "fb_page_id": None,
        "fb_form_id": None,
        "fb_adgroup_id": None,
        "fb_ad_id": None,
        "first_name": "",
        "last_name": "",
        "email": None,
        "phone": None,
        "course": None,
        "client_comments": None,
        "current_download": None,
        "location": None,
        "language": "en",
        "utm_url": None,
        "utm_medium": None,
        "utm_campaign": None,
        "utm_content": None,
        "utm_source": None,
        "referral_key": None,
        "gclid": None,
        "tags": "",
        "automations": "",
        "street_address": None,
        "sex": None,
        "country": None,
        "city": None,
        "custom_fields": None,
        "latitude": None,
        "longitude": None,
        "state": None,
        "zip_code": None,
        "browser_lang": None,
        "storage_status": "PENDING",
        "storage_status_text": "",
        "lead_type": None,
        "deal_status": None,
        "sentiment": None,
        "ac_contact_id": None,
        "ac_deal_id": None,
        "ac_expected_cohort": None,
        "utm_placement": None,
        "utm_plan": None,
        "utm_term": None,
        "won_at": None,
        "contact_id": None,
        "academy_id": None,
        "user_id": None,
        "lead_generation_app_id": None,
        "ac_deal_course": None,
        "ac_deal_location": None,
        "ac_deal_owner_full_name": None,
        "ac_deal_owner_id": None,
        "ac_expected_cohort_date": None,
        "ac_deal_amount": None,
        "ac_deal_currency_code": None,
        **data,
    }


def form_entry_serializer(self, data={}):
    return {
        "id": 1,
        "fb_leadgen_id": None,
        "fb_page_id": None,
        "fb_form_id": None,
        "fb_adgroup_id": None,
        "fb_ad_id": None,
        "first_name": "",
        "last_name": "",
        "email": None,
        "phone": None,
        "course": None,
        "client_comments": None,
        "custom_fields": None,
        "location": None,
        "language": "en",
        "utm_url": None,
        "utm_medium": None,
        "utm_campaign": None,
        "utm_content": None,
        "utm_source": None,
        "utm_term": None,
        "utm_placement": None,
        "utm_plan": None,
        "current_download": None,
        "referral_key": None,
        "gclid": None,
        "tags": "",
        "automations": "",
        "street_address": None,
        "sex": None,
        "country": None,
        "city": None,
        "latitude": None,
        "longitude": None,
        "state": None,
        "zip_code": None,
        "browser_lang": None,
        "storage_status": "PENDING",
        "storage_status_text": "",
        "lead_type": None,
        "deal_status": None,
        "sentiment": None,
        "ac_expected_cohort": None,
        "ac_contact_id": None,
        "ac_deal_id": None,
        "won_at": None,
        "created_at": self.bc.datetime.to_iso_string(UTC_NOW),
        "updated_at": self.bc.datetime.to_iso_string(UTC_NOW),
        "contact": None,
        "academy": None,
        "lead_generation_app": None,
        "user": None,
        "ac_deal_course": None,
        "ac_deal_location": None,
        "ac_deal_owner_full_name": None,
        "ac_deal_owner_id": None,
        "ac_expected_cohort_date": None,
        "ac_deal_amount": None,
        "ac_deal_currency_code": None,
        **data,
    }


class CreateFormEntryTestSuite(MarketingTestCase):

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    def test_create_form_entry_with_dict_empty_without_csv_upload_id(self):
        """Test create_form_entry task without data"""

        create_form_entry.delay(1, **{})

        self.assertEqual(self.count_form_entry(), 0)
        self.assertEqual(self.bc.database.list_of("monitoring.CSVUpload"), [])
        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Create form entry started"),
                call("Create form entry started"),
            ],
        )
        self.assertEqual(logging.Logger.error.call_args_list, [call("No CSVUpload found with this id", exc_info=True)])

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("breathecode.marketing.tasks.persist_single_lead.delay", MagicMock())
    def test_create_form_entry_with_dict_empty_with_csv_upload_id(self):
        """Test create_form_entry task without data"""

        model = self.bc.database.create(csv_upload={"log": ""})
        logging.Logger.info.call_args_list = []
        create_form_entry.delay(1, **{})

        self.assertEqual(self.count_form_entry(), 0)
        self.assertEqual(
            self.bc.database.list_of("monitoring.CSVUpload"),
            [
                {
                    **self.bc.format.to_dict(model.csv_upload),
                    "status": "ERROR",
                    "finished_at": UTC_NOW,
                    "log": "No first name in form entry, No last name in form entry, No email "
                    "in form entry, No location or academy in form entry. ",
                }
            ],
        )
        self.assertEqual(logging.Logger.info.call_args_list, [call("Create form entry started")])
        self.assertEqual(
            logging.Logger.error.call_args_list,
            [
                call("No first name in form entry"),
                call("No last name in form entry"),
                call("No email in form entry"),
                call("No location or academy in form entry"),
                call("Missing field in received item"),
                call({}),
                call(
                    "No first name in form entry, No last name in form entry, No email in form entry, No location or academy in form entry. ",
                    exc_info=True,
                ),
            ],
        )

        self.assertEqual(tasks.persist_single_lead.delay.call_args_list, [])

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("breathecode.marketing.tasks.persist_single_lead.delay", MagicMock())
    def test_create_form_entry_with_dict_check_regex(self):
        """Test create_form_entry task without data"""
        cases = [
            (
                "Brandon" + self.bc.random.string(number=True, size=1),
                "Smith" + self.bc.random.string(number=True, size=1),
                "test12.net",
            ),
            (
                "Brandon" + self.bc.random.string(symbol=True, size=1),
                "Smith" + self.bc.random.string(symbol=True, size=1),
                "test12@.net",
            ),
            (
                "Brandon" + self.bc.random.string(symbol=True, size=1),
                "Smith" + self.bc.random.string(symbol=True, size=1),
                "test12.net@",
            ),
            (
                "Brandon" + self.bc.random.string(symbol=True, size=1),
                "Smith" + self.bc.random.string(symbol=True, size=1),
                "@test12.net",
            ),
        ]

        model = self.bc.database.create(csv_upload={"log": ""})

        for first_name, last_name, email in cases:
            slug = self.bc.fake.slug()
            logging.Logger.info.call_args_list = []
            logging.Logger.error.call_args_list = []

            model.csv_upload.log = ""
            model.csv_upload.save()

            data = {
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "location": "Madrid",
                "academy": slug,
            }
            create_form_entry.delay(1, **data)

            self.assertEqual(self.count_form_entry(), 0)
            self.assertEqual(
                self.bc.database.list_of("monitoring.CSVUpload"),
                [
                    {
                        **self.bc.format.to_dict(model.csv_upload),
                        "status": "ERROR",
                        "finished_at": UTC_NOW,
                        "log": f"No academy exists with this academy active_campaign_slug: {slug}, "
                        f"No academy exists with this academy slug: {slug}, first "
                        "name has incorrect characters, last name has incorrect characters, "
                        "email has incorrect format, No location or academy in form entry. ",
                    }
                ],
            )
            self.assertEqual(logging.Logger.info.call_args_list, [call("Create form entry started")])
            self.assertEqual(
                logging.Logger.error.call_args_list,
                [
                    call(f'No academy exists with this academy active_campaign_slug: {data["academy"]}'),
                    call(f'No academy exists with this academy slug: {data["academy"]}'),
                    call("first name has incorrect characters"),
                    call("last name has incorrect characters"),
                    call("email has incorrect format"),
                    call("No location or academy in form entry"),
                    call("Missing field in received item"),
                    call(data),
                    call(
                        f"No academy exists with this academy active_campaign_slug: {slug}, No "
                        f"academy exists with this academy slug: {slug}, first name has incorrect characters, "
                        "last name has incorrect characters, email has incorrect format, No location or "
                        "academy in form entry. ",
                        exc_info=True,
                    ),
                ],
            )
            self.assertEqual(tasks.persist_single_lead.delay.call_args_list, [])

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("breathecode.marketing.tasks.persist_single_lead.delay", MagicMock())
    @patch("uuid.UUID.int", PropertyMock(return_value=1000))
    def test_create_form_entry_with_dict_with_correct_format(self):
        """Test create_form_entry task without data"""

        model = self.bc.database.create(csv_upload={"log": ""}, academy={"active_campaign_slug": self.bc.fake.slug()})

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        data = {
            "first_name": "John",
            "last_name": "Smith",
            "email": "test@gmail.com",
            "location": model.academy.active_campaign_slug,
            "academy": model.academy.slug,
        }
        create_form_entry.delay(1, **data)

        del data["academy"]

        self.assertEqual(
            self.bc.database.list_of("marketing.FormEntry"),
            [
                form_entry_field(
                    {
                        **data,
                        "attribution_id": "75b36c508866d18732305da14fe9a0",
                        "academy_id": 1,
                    }
                )
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("monitoring.CSVUpload"),
            [
                {
                    **self.bc.format.to_dict(model.csv_upload),
                    "status": "DONE",
                    "finished_at": UTC_NOW,
                }
            ],
        )
        self.assertEqual(
            logging.Logger.info.call_args_list,
            [call("Create form entry started"), call("create_form_entry successfully created")],
        )
        self.assertEqual(logging.Logger.error.call_args_list, [])

        self.bc.check.calls(
            tasks.persist_single_lead.delay.call_args_list,
            [
                call(
                    form_entry_serializer(
                        self,
                        {
                            **data,
                            "academy": 1,
                            "attribution_id": "75b36c508866d18732305da14fe9a0",
                        },
                    )
                ),
            ],
        )
