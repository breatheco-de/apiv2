"""
Test /answer/:id
"""

import requests
from breathecode.marketing.tasks import persist_single_lead
import logging
import string, os
from unittest.mock import patch, MagicMock, call

from random import choice, choices, randint
from breathecode.tests.mocks import (
    OLD_BREATHECODE_INSTANCES,
    apply_old_breathecode_requests_request_mock,
    apply_requests_get_mock,
)
from breathecode.tests.mocks.requests import apply_requests_post_mock
from ..mixins import MarketingTestCase
from faker import Faker

MAILGUN_URL = f"https://api.mailgun.net/v3/{os.environ.get('MAILGUN_DOMAIN')}/messages"

GOOGLE_CLOUD_KEY = os.getenv("GOOGLE_CLOUD_KEY", None)
GOOGLE_MAPS_URL = (
    "https://maps.googleapis.com/maps/api/geocode/json?latlng=15.000000000000000,"
    f"15.000000000000000&key={GOOGLE_CLOUD_KEY}"
)

GOOGLE_MAPS_INVALID_REQUEST = {
    "status": "INVALID_REQUEST",
}

GOOGLE_MAPS_OK = {
    "status": "OK",
    "results": [
        {
            "address_components": [
                {
                    "types": {
                        "country": "US",
                    },
                    "long_name": "US",
                },
                {
                    "types": {
                        "locality": "New York",
                    },
                    "long_name": "New York",
                },
                {
                    "types": {
                        "route": "Avenue",
                    },
                    "long_name": "Avenue",
                },
                {
                    "types": {"postal_code": "10028"},
                    "long_name": "10028",
                },
            ]
        }
    ],
}


def random_string():
    return "".join(choices(string.ascii_letters, k=10))


def fix_db_field(data={}):
    del data["ac_academy"]
    return data


fake = Faker()
fake_url = fake.url()


def generate_form_entry_kwargs(kwargs={}):
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
        "zip_code": str(randint(0, 9999)),
        "browser_lang": random_string(),
        "storage_status": choice(["PENDING", "PERSISTED"]),
        "lead_type": choice(["STRONG", "SOFT", "DISCOVERY"]),
        "deal_status": choice(["WON", "LOST"]),
        "sentiment": choice(["GOOD", "BAD"]),
        "current_download": fake_url,
        **kwargs,
    }


class AnswerIdTestSuite(MarketingTestCase):
    """
    🔽🔽🔽 Passing None
    """

    @patch("requests.get", apply_requests_get_mock([(200, GOOGLE_MAPS_URL, GOOGLE_MAPS_OK)]))
    @patch("requests.post", apply_requests_post_mock([(201, MAILGUN_URL, "ok")]))
    @patch("requests.request", apply_old_breathecode_requests_request_mock())
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    def test_passing_none(self):
        data = None

        persist_single_lead.delay(data)

        self.assertEqual(self.count_form_entry(), 0)
        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting persist_single_lead"),
            ],
        )
        self.assertEqual(logging.Logger.error.call_args_list, [])

        self.assertEqual(requests.get.error.call_args_list, [])
        self.assertEqual(requests.post.error.call_args_list, [])
        self.assertEqual(requests.request.error.call_args_list, [])

        self.assertEqual(self.bc.database.list_of("marketing.FormEntry"), [])

    """
    🔽🔽🔽 Passing empty dict
    """

    @patch("requests.get", apply_requests_get_mock([(200, GOOGLE_MAPS_URL, GOOGLE_MAPS_OK)]))
    @patch("requests.post", apply_requests_post_mock([(201, MAILGUN_URL, "ok")]))
    @patch("requests.request", apply_old_breathecode_requests_request_mock())
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    def test_empty_dict(self):
        data = {}

        persist_single_lead.delay(data)

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting persist_single_lead"),
            ],
        )
        self.assertEqual(logging.Logger.error.call_args_list, [])

        self.assertEqual(requests.get.error.call_args_list, [])
        self.assertEqual(requests.post.error.call_args_list, [])
        self.assertEqual(requests.request.error.call_args_list, [])

        self.assertEqual(self.bc.database.list_of("marketing.FormEntry"), [])

    """
    🔽🔽🔽 Passing dict with bad location
    """

    @patch("requests.get", apply_requests_get_mock([(200, GOOGLE_MAPS_URL, GOOGLE_MAPS_OK)]))
    @patch("requests.post", apply_requests_post_mock([(201, MAILGUN_URL, "ok")]))
    @patch("requests.request", apply_old_breathecode_requests_request_mock())
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    def test_dict_with_bad_location(self):
        data = {"location": "they-killed-kenny"}

        persist_single_lead.delay(data)

        self.assertEqual(self.count_form_entry(), 0)
        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting persist_single_lead"),
                # retrying
                call("Starting persist_single_lead"),
            ],
        )
        self.assertEqual(
            logging.Logger.error.call_args_list, [call("No academy found with slug they-killed-kenny", exc_info=True)]
        )

        self.assertEqual(requests.get.error.call_args_list, [])
        self.assertEqual(requests.post.error.call_args_list, [])
        self.assertEqual(requests.request.error.call_args_list, [])

        self.assertEqual(self.bc.database.list_of("marketing.FormEntry"), [])

    """
    🔽🔽🔽 Passing dict with Academy.slug as location
    """

    @patch("requests.get", apply_requests_get_mock([(200, GOOGLE_MAPS_URL, GOOGLE_MAPS_OK)]))
    @patch("requests.post", apply_requests_post_mock([(201, MAILGUN_URL, "ok")]))
    @patch("requests.request", apply_old_breathecode_requests_request_mock())
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    def test_dict_with_location(self):
        """Test /answer/:id without auth"""
        model = self.generate_models(academy=True, active_campaign_academy=True)

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        data = {"location": model["academy"].slug}

        persist_single_lead.delay(data)

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting persist_single_lead"),
                call("automations not found"),
            ],
        )
        self.assertEqual(
            logging.Logger.error.call_args_list,
            [
                call("You need to specify tags for this entry", exc_info=True),
            ],
        )

        self.assertEqual(requests.get.error.call_args_list, [])
        self.assertEqual(requests.post.error.call_args_list, [])
        self.assertEqual(requests.request.error.call_args_list, [])

        self.assertEqual(self.bc.database.list_of("marketing.FormEntry"), [])

    """
    🔽🔽🔽 Passing dict with AcademyAlias.active_campaign_slug as location
    """

    @patch("requests.get", apply_requests_get_mock([(200, GOOGLE_MAPS_URL, GOOGLE_MAPS_OK)]))
    @patch("requests.post", apply_requests_post_mock([(201, MAILGUN_URL, "ok")]))
    @patch("requests.request", apply_old_breathecode_requests_request_mock())
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    def test_with_location_academy_alias(self):
        """Test /answer/:id without auth"""
        model = self.generate_models(
            academy=True,
            active_campaign_academy=True,
            academy_alias=True,
            academy_alias_kwargs={"active_campaign_slug": "odin"},
        )

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        data = {"location": "odin"}

        persist_single_lead.delay(data)

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting persist_single_lead"),
                call("automations not found"),
            ],
        )
        self.assertEqual(
            logging.Logger.error.call_args_list,
            [
                call("You need to specify tags for this entry", exc_info=True),
            ],
        )

        self.assertEqual(requests.get.error.call_args_list, [])
        self.assertEqual(requests.post.error.call_args_list, [])
        self.assertEqual(requests.request.error.call_args_list, [])

        self.assertEqual(self.bc.database.list_of("marketing.FormEntry"), [])

    """
    🔽🔽🔽 Passing dict with AcademyAlias.active_campaign_slug as location and bad tags
    """

    @patch("requests.get", apply_requests_get_mock([(200, GOOGLE_MAPS_URL, GOOGLE_MAPS_OK)]))
    @patch("requests.post", apply_requests_post_mock([(201, MAILGUN_URL, "ok")]))
    @patch("requests.request", apply_old_breathecode_requests_request_mock())
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    def test_with_bad_tags(self):
        """Test /answer/:id without auth"""
        model = self.generate_models(academy=True, active_campaign_academy=True)

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        data = {
            "location": model["academy"].slug,
            "tags": "they-killed-kenny",
        }

        persist_single_lead.delay(data)

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting persist_single_lead"),
                call("automations not found"),
            ],
        )

        self.assertEqual(
            str(logging.Logger.error.call_args_list),
            str(
                [
                    call(
                        "Some tag applied to the contact not found or have tag_type different than [STRONG, SOFT, DISCOVER, OTHER]: Check for the follow tags:  they-killed-kenny",
                        exc_info=True,
                    ),
                ]
            ),
        )

        self.assertEqual(requests.get.error.call_args_list, [])
        self.assertEqual(requests.post.error.call_args_list, [])
        self.assertEqual(requests.request.error.call_args_list, [])

        self.assertEqual(self.bc.database.list_of("marketing.FormEntry"), [])

    """
    🔽🔽🔽 Passing dict with AcademyAlias.active_campaign_slug as location and Tag.slug as tags of type STRONG
    """

    @patch("requests.get", apply_requests_get_mock([(200, GOOGLE_MAPS_URL, GOOGLE_MAPS_OK)]))
    @patch("requests.post", apply_requests_post_mock([(201, MAILGUN_URL, "ok")]))
    @patch("requests.request", apply_old_breathecode_requests_request_mock())
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    def test_with_tag_type_strong(self):
        """Test /answer/:id without auth"""

        model = self.generate_models(academy=1, active_campaign_academy=1, tag={"tag_type": "STRONG"})

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        data = {
            "location": model["academy"].slug,
            "tags": model["tag"].slug,
        }

        persist_single_lead.delay(data)

        self.assertEqual(self.bc.database.list_of("marketing.FormEntry"), [])
        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting persist_single_lead"),
                call("automations not found"),
                call("found tags"),
                call({model.tag.slug}),
            ],
        )
        self.assertEqual(
            logging.Logger.error.call_args_list,
            [
                call("No automation was specified and the the specified tag has no automation either", exc_info=True),
            ],
        )

        self.assertEqual(requests.get.error.call_args_list, [])
        self.assertEqual(requests.post.error.call_args_list, [])
        self.assertEqual(requests.request.error.call_args_list, [])

    """
    🔽🔽🔽 With one Automation but not found
    """

    @patch("requests.get", apply_requests_get_mock([(200, GOOGLE_MAPS_URL, GOOGLE_MAPS_OK)]))
    @patch("requests.post", apply_requests_post_mock([(201, MAILGUN_URL, "ok")]))
    @patch("requests.request", apply_old_breathecode_requests_request_mock())
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    def test_with_tag_type_strong__with_automation(self):
        """Test /answer/:id without auth"""
        model = self.generate_models(academy=1, active_campaign_academy=1, tag={"tag_type": "STRONG"}, automation=1)

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        data = {
            "location": model["academy"].slug,
            "tags": model["tag"].slug,
        }

        persist_single_lead.delay(data)

        self.assertEqual(self.bc.database.list_of("marketing.FormEntry"), [])
        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting persist_single_lead"),
                call("automations not found"),
                call("found tags"),
                call({model.tag.slug}),
            ],
        )
        self.assertEqual(logging.Logger.error.call_args_list, [call("The email doesn't exist", exc_info=True)])

        self.assertEqual(requests.get.error.call_args_list, [])
        self.assertEqual(requests.post.error.call_args_list, [])
        self.assertEqual(requests.request.error.call_args_list, [])

    """
    🔽🔽🔽 Dict with bad automations and with one Automation but not found
    """

    @patch("requests.get", apply_requests_get_mock([(200, GOOGLE_MAPS_URL, GOOGLE_MAPS_OK)]))
    @patch("requests.post", apply_requests_post_mock([(201, MAILGUN_URL, "ok")]))
    @patch("requests.request", apply_old_breathecode_requests_request_mock())
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    def test_with_automations__not_found(self):
        """Test /answer/:id without auth"""
        model = self.generate_models(academy=1, active_campaign_academy=1, tag={"tag_type": "STRONG"}, automation=1)

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        data = {"location": model["academy"].slug, "tags": model["tag"].slug, "automations": "they-killed-kenny"}

        persist_single_lead.delay(data)

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting persist_single_lead"),
            ],
        )
        self.assertEqual(
            logging.Logger.error.call_args_list,
            [
                call("The specified automation they-killed-kenny was not found for this AC Academy", exc_info=True),
            ],
        )

        self.assertEqual(requests.get.error.call_args_list, [])
        self.assertEqual(requests.post.error.call_args_list, [])
        self.assertEqual(requests.request.error.call_args_list, [])

        self.assertEqual(self.bc.database.list_of("marketing.FormEntry"), [])

    """
    🔽🔽🔽 Dict with automations, without email and with one Automation found
    """

    @patch("requests.get", apply_requests_get_mock([(200, GOOGLE_MAPS_URL, GOOGLE_MAPS_OK)]))
    @patch("requests.post", apply_requests_post_mock([(201, MAILGUN_URL, "ok")]))
    @patch("requests.request", apply_old_breathecode_requests_request_mock())
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    def test_with_automations_slug(self):
        """Test /answer/:id without auth"""
        model = self.generate_models(
            academy=1, active_campaign_academy=1, tag={"tag_type": "STRONG"}, automation={"slug": "they-killed-kenny"}
        )

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        data = {"location": model["academy"].slug, "tags": model["tag"].slug, "automations": model["automation"].slug}

        persist_single_lead.delay(data)

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting persist_single_lead"),
                call("found automations"),
                call([model.automation.acp_id]),
                call("found tags"),
                call({model.tag.slug}),
            ],
        )

        self.assertEqual(logging.Logger.error.call_args_list, [call("The email doesn't exist", exc_info=True)])

        self.assertEqual(requests.get.error.call_args_list, [])
        self.assertEqual(requests.post.error.call_args_list, [])
        self.assertEqual(requests.request.error.call_args_list, [])

        self.assertEqual(self.bc.database.list_of("marketing.FormEntry"), [])

    """
    🔽🔽🔽 With email in dict
    """

    @patch("requests.get", apply_requests_get_mock([(200, GOOGLE_MAPS_URL, GOOGLE_MAPS_OK)]))
    @patch("requests.post", apply_requests_post_mock([(201, MAILGUN_URL, "ok")]))
    @patch("requests.request", apply_old_breathecode_requests_request_mock())
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    def test_with_email(self):
        """Test /answer/:id without auth"""
        model = self.generate_models(
            academy=True,
            active_campaign_academy=True,
            tag=True,
            tag_kwargs={"tag_type": "STRONG"},
            automation=True,
            automation_kwargs={"slug": "they-killed-kenny"},
        )

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        data = {
            "location": model["academy"].slug,
            "tags": model["tag"].slug,
            "automations": model["automation"].slug,
            "email": "pokemon@potato.io",
        }

        persist_single_lead.delay(data)

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting persist_single_lead"),
                call("found automations"),
                call([model.automation.acp_id]),
                call("found tags"),
                call({model.tag.slug}),
            ],
        )

        self.assertEqual(
            logging.Logger.error.call_args_list,
            [
                call("The first name doesn't exist", exc_info=True),
            ],
        )

        self.assertEqual(requests.get.error.call_args_list, [])
        self.assertEqual(requests.post.error.call_args_list, [])
        self.assertEqual(requests.request.error.call_args_list, [])

        self.assertEqual(self.bc.database.list_of("marketing.FormEntry"), [])

    """
    🔽🔽🔽 With first_name in dict
    """

    @patch("requests.get", apply_requests_get_mock([(200, GOOGLE_MAPS_URL, GOOGLE_MAPS_OK)]))
    @patch("requests.post", apply_requests_post_mock([(201, MAILGUN_URL, "ok")]))
    @patch("requests.request", apply_old_breathecode_requests_request_mock())
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    def test_with_first_name(self):
        """Test /answer/:id without auth"""
        model = self.generate_models(
            academy=True,
            active_campaign_academy=True,
            tag=True,
            tag_kwargs={"tag_type": "STRONG"},
            automation=True,
            automation_kwargs={"slug": "they-killed-kenny"},
        )

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        data = {
            "location": model["academy"].slug,
            "tags": model["tag"].slug,
            "automations": model["automation"].slug,
            "email": "pokemon@potato.io",
            "first_name": "Konan",
        }

        persist_single_lead.delay(data)

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting persist_single_lead"),
                call("found automations"),
                call([model.automation.acp_id]),
                call("found tags"),
                call({model.tag.slug}),
            ],
        )

        self.assertEqual(
            logging.Logger.error.call_args_list,
            [
                call("The last name doesn't exist", exc_info=True),
            ],
        )

        self.assertEqual(requests.get.error.call_args_list, [])
        self.assertEqual(requests.post.error.call_args_list, [])
        self.assertEqual(requests.request.error.call_args_list, [])

        self.assertEqual(self.bc.database.list_of("marketing.FormEntry"), [])

    """
    🔽🔽🔽 With last_name in dict
    """

    @patch("requests.get", apply_requests_get_mock([(200, GOOGLE_MAPS_URL, GOOGLE_MAPS_OK)]))
    @patch("requests.post", apply_requests_post_mock([(201, MAILGUN_URL, "ok")]))
    @patch("requests.request", apply_old_breathecode_requests_request_mock())
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    def test_with_last_name(self):
        """Test /answer/:id without auth"""
        model = self.generate_models(
            academy=True,
            active_campaign_academy=True,
            tag=True,
            tag_kwargs={"tag_type": "STRONG"},
            automation=True,
            automation_kwargs={"slug": "they-killed-kenny"},
        )

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        data = {
            "location": model["academy"].slug,
            "tags": model["tag"].slug,
            "automations": model["automation"].slug,
            "email": "pokemon@potato.io",
            "first_name": "Konan",
            "last_name": "Amegakure",
        }

        persist_single_lead.delay(data)

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting persist_single_lead"),
                call("found automations"),
                call([model.automation.acp_id]),
                call("found tags"),
                call({model.tag.slug}),
            ],
        )

        self.assertEqual(
            logging.Logger.error.call_args_list,
            [
                call("The phone doesn't exist", exc_info=True),
            ],
        )

        self.assertEqual(requests.get.error.call_args_list, [])
        self.assertEqual(requests.post.error.call_args_list, [])
        self.assertEqual(requests.request.error.call_args_list, [])

        self.assertEqual(self.bc.database.list_of("marketing.FormEntry"), [])

    """
    🔽🔽🔽 With phone in dict
    """

    @patch("requests.get", apply_requests_get_mock([(200, GOOGLE_MAPS_URL, GOOGLE_MAPS_OK)]))
    @patch("requests.post", apply_requests_post_mock([(201, MAILGUN_URL, "ok")]))
    @patch("requests.request", apply_old_breathecode_requests_request_mock())
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    def test_with_phone(self):
        """Test /answer/:id without auth"""
        model = self.generate_models(
            academy=True,
            active_campaign_academy=True,
            tag=True,
            tag_kwargs={"tag_type": "STRONG"},
            automation=True,
            automation_kwargs={"slug": "they-killed-kenny"},
        )

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        data = {
            "location": model["academy"].slug,
            "tags": model["tag"].slug,
            "automations": model["automation"].slug,
            "email": "pokemon@potato.io",
            "first_name": "Konan",
            "last_name": "Amegakure",
            "phone": "123123123",
        }

        persist_single_lead.delay(data)

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting persist_single_lead"),
                call("found automations"),
                call([model.automation.acp_id]),
                call("found tags"),
                call({model.tag.slug}),
            ],
        )
        self.assertEqual(
            logging.Logger.error.call_args_list,
            [
                call("The id doesn't exist", exc_info=True),
            ],
        )

        self.assertEqual(requests.get.error.call_args_list, [])
        self.assertEqual(requests.post.error.call_args_list, [])
        self.assertEqual(requests.request.error.call_args_list, [])

        self.assertEqual(self.bc.database.list_of("marketing.FormEntry"), [])

    """
    🔽🔽🔽 With id in dict but FormEntry doesn't exist
    """

    @patch("requests.get", apply_requests_get_mock([(200, GOOGLE_MAPS_URL, GOOGLE_MAPS_OK)]))
    @patch("requests.post", apply_requests_post_mock([(201, MAILGUN_URL, "ok")]))
    @patch("requests.request", apply_old_breathecode_requests_request_mock())
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    def test_with_id(self):
        """Test /answer/:id without auth"""
        model = self.generate_models(
            academy=True,
            active_campaign_academy=True,
            tag=True,
            tag_kwargs={"tag_type": "STRONG"},
            automation=True,
            automation_kwargs={"slug": "they-killed-kenny"},
        )

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        data = {
            "location": model["academy"].slug,
            "tags": model["tag"].slug,
            "automations": model["automation"].slug,
            "email": "pokemon@potato.io",
            "first_name": "Konan",
            "last_name": "Amegakure",
            "phone": "123123123",
            "id": 123123123,
            "course": "asdasd",
        }

        persist_single_lead.delay(data)

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting persist_single_lead"),
                call("found automations"),
                call([model.automation.acp_id]),
                call("found tags"),
                call({model.tag.slug}),
            ],
        )

        self.assertEqual(
            logging.Logger.error.call_args_list,
            [
                call("FormEntry not found (id: 123123123)", exc_info=True),
            ],
        )

        self.assertEqual(requests.get.error.call_args_list, [])
        self.assertEqual(requests.post.error.call_args_list, [])
        self.assertEqual(requests.request.error.call_args_list, [])

        self.assertEqual(self.bc.database.list_of("marketing.FormEntry"), [])

    """
    🔽🔽🔽 With id and without course in dict, FormEntry exists
    """

    @patch("requests.get", apply_requests_get_mock([(200, GOOGLE_MAPS_URL, GOOGLE_MAPS_INVALID_REQUEST)]))
    @patch("requests.post", apply_requests_post_mock([(201, MAILGUN_URL, "ok")]))
    @patch("requests.request", apply_old_breathecode_requests_request_mock())
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    def test_with_form_entry_with_data_invalid(self):
        mock_old_breathecode = OLD_BREATHECODE_INSTANCES["request"]
        mock_old_breathecode.call_args_list = []
        model = self.generate_models(
            academy=True,
            active_campaign_academy=True,
            tag=True,
            tag_kwargs={"tag_type": "STRONG"},
            automation=True,
            automation_kwargs={"slug": "they-killed-kenny"},
            form_entry=True,
            form_entry_kwargs=generate_form_entry_kwargs(),
            active_campaign_academy_kwargs={"ac_url": "https://old.hardcoded.breathecode.url"},
        )

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        data = {
            "location": model["academy"].slug,
            "tags": model["tag"].slug,
            "automations": model["automation"].slug,
            "email": "pokemon@potato.io",
            "first_name": "Konan",
            "last_name": "Amegakure",
            "phone": "123123123",
            "id": model["form_entry"].id,
        }

        persist_single_lead.delay(data)

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting persist_single_lead"),
                call("found automations"),
                call([model.automation.acp_id]),
                call("found tags"),
                call({model.tag.slug}),
            ],
        )

        self.assertEqual(
            logging.Logger.error.call_args_list,
            [
                call("The course doesn't exist", exc_info=True),
            ],
        )

        self.assertEqual(requests.get.call_args_list, [])
        self.assertEqual(requests.post.call_args_list, [])
        self.assertEqual(requests.request.call_args_list, [])

        db = self.bc.format.to_dict(model["form_entry"])
        del db["ac_academy"]

        self.assertEqual(
            self.bc.database.list_of("marketing.FormEntry"),
            [
                {
                    **db,
                    "ac_contact_id": None,
                    "storage_status": "ERROR",
                    "storage_status_text": "The course doesn't exist",
                }
            ],
        )

    # """
    # 🔽🔽🔽 First successful response, with id in dict, FormEntry found
    # """

    # @patch('requests.get', apply_requests_get_mock([(200, GOOGLE_MAPS_URL, GOOGLE_MAPS_OK)]))
    # @patch('requests.post', apply_requests_post_mock([(201, MAILGUN_URL, 'ok')]))
    # @patch('requests.request', apply_old_breathecode_requests_request_mock())
    # @patch('logging.Logger.info', MagicMock())
    # @patch('logging.Logger.error', MagicMock())
    # def test_with_form_entry_with_data(self):
    #     """Test /answer/:id without auth"""

    #     mock_old_breathecode = OLD_BREATHECODE_INSTANCES['request']
    #     mock_old_breathecode.call_args_list = []
    #     model = self.generate_models(
    #         academy=1,
    #         active_campaign_academy={'ac_url': 'https://old.hardcoded.breathecode.url'},
    #         tag={'tag_type': 'STRONG'},
    #         automation={'slug': 'they-killed-kenny'},
    #         form_entry=generate_form_entry_kwargs())

    #     logging.Logger.info.call_args_list = []
    #     logging.Logger.error.call_args_list = []

    #     data = {
    #         'location': model['academy'].slug,
    #         'tags': model['tag'].slug,
    #         'automations': model['automation'].slug,
    #         'email': 'pokemon@potato.io',
    #         'first_name': 'Konan',
    #         'last_name': 'Amegakure',
    #         'phone': '123123123',
    #         'id': model['form_entry'].id,
    #         'course': 'asdasd',
    #     }

    #     persist_single_lead.delay(data)

    #     db = self.bc.format.to_dict(model['form_entry'])
    #     del db['ac_academy']

    #     self.assertEqual(self.bc.database.list_of('marketing.FormEntry'), [{
    #         **db,
    #         'ac_contact_id': '1',
    #         'storage_status': 'PERSISTED',
    #         'storage_status_text': '',
    #     }])

    #     self.assertEqual(logging.Logger.info.call_args_list, [
    #         call('Starting persist_single_lead'),
    #         call('found automations'),
    #         call([model.automation.acp_id]),
    #         call('found tags'),
    #         call({model.tag.slug}),
    #         call('ready to send contact with following details: ' + str({
    #             'email': 'pokemon@potato.io',
    #             'first_name': 'Konan',
    #             'last_name': 'Amegakure',
    #             'phone': '123123123',
    #             'field[18,0]': model.academy.slug,
    #             'field[2,0]': 'asdasd',
    #         })),
    #         call(f'Triggered automation with id {model.automation.acp_id} ' + str({
    #             'subscriber_id': 1,
    #             'result_code': 1,
    #             'contacts': [{
    #                 'id': 1
    #             }]
    #         })),
    #         call('automations was executed successfully'),
    #         call('contact was tagged successfully'),
    #     ])
    #     self.assertEqual(logging.Logger.error.call_args_list, [])

    #     self.assertEqual(requests.get.call_args_list, [])
    #     self.assertEqual(requests.post.call_args_list, [])
    #     self.assertEqual(requests.request.call_args_list, [
    #         call('POST',
    #              'https://old.hardcoded.breathecode.url/admin/api.php',
    #              params=[
    #                  ('api_action', 'contact_sync'),
    #                  ('api_key', model['active_campaign_academy'].ac_key),
    #                  ('api_output', 'json'),
    #              ],
    #              data={
    #                  'email': 'pokemon@potato.io',
    #                  'first_name': 'Konan',
    #                  'last_name': 'Amegakure',
    #                  'phone': '123123123',
    #                  'field[18,0]': model['academy'].slug,
    #                  'field[2,0]': 'asdasd',
    #              },
    #              timeout=2),
    #         call('POST',
    #              'https://old.hardcoded.breathecode.url/api/3/contactAutomations',
    #              headers={
    #                  'Accept': 'application/json',
    #                  'Content-Type': 'application/json',
    #                  'Api-Token': model['active_campaign_academy'].ac_key
    #              },
    #              json={'contactAutomation': {
    #                  'contact': 1,
    #                  'automation': model['automation'].acp_id
    #              }},
    #              timeout=2),
    #         call('POST',
    #              'https://old.hardcoded.breathecode.url/api/3/contactTags',
    #              headers={
    #                  'Accept': 'application/json',
    #                  'Content-Type': 'application/json',
    #                  'Api-Token': model['active_campaign_academy'].ac_key
    #              },
    #              json={'contactTag': {
    #                  'contact': 1,
    #                  'tag': model['tag'].acp_id
    #              }},
    #              timeout=2)
    #     ])
    """
    🔽🔽🔽 First successful response, with id in dict, FormEntry found two times
    """

    @patch("requests.get", apply_requests_get_mock([(200, GOOGLE_MAPS_URL, GOOGLE_MAPS_OK)]))
    @patch("requests.post", apply_requests_post_mock([(201, MAILGUN_URL, "ok")]))
    @patch("requests.request", apply_old_breathecode_requests_request_mock())
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    def test_with_form_entry_with_data__two_form_entries_found(self):
        """Test /answer/:id without auth"""
        form_entries = [
            generate_form_entry_kwargs(
                {
                    "email": "pokemon@potato.io",
                    "course": "asdasd",
                    "storage_status": "PERSISTED",
                }
            ),
            generate_form_entry_kwargs(
                {
                    "email": "pokemon@potato.io",
                    "course": "asdasd",
                    "storage_status": "PERSISTED",
                }
            ),
        ]

        model = self.generate_models(
            academy=True,
            active_campaign_academy=True,
            tag=True,
            tag_kwargs={"tag_type": "STRONG"},
            automation=True,
            automation_kwargs={"slug": "they-killed-kenny"},
            form_entry=form_entries,
            active_campaign_academy_kwargs={"ac_url": "https://old.hardcoded.breathecode.url"},
        )

        logging.Logger.info.call_args_list = []
        logging.Logger.error.call_args_list = []

        data = {
            "location": model["academy"].slug,
            "tags": model["tag"].slug,
            "automations": model["automation"].slug,
            "email": "pokemon@potato.io",
            "first_name": "Konan",
            "last_name": "Amegakure",
            "phone": "123123123",
            "course": "asdasd",
            "id": 2,
        }

        persist_single_lead.delay(data)
        form = self.get_form_entry(1)

        db = self.bc.format.to_dict(model["form_entry"][1])
        del db["ac_academy"]

        self.assertEqual(
            self.bc.database.list_of("marketing.FormEntry"),
            [
                fix_db_field(self.bc.format.to_dict(model.form_entry[0])),
                {
                    **db,
                    "ac_contact_id": "1",
                    "ac_expected_cohort": None,
                    "latitude": form.latitude,
                    "longitude": form.longitude,
                    "storage_status": "DUPLICATED",
                    "lead_generation_app_id": None,
                    "storage_status_text": "",
                },
            ],
        )

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call("Starting persist_single_lead"),
                call("found automations"),
                call([model.automation.acp_id]),
                call("found tags"),
                call({model.tag.slug}),
                call(
                    "ready to send contact with following details: "
                    + str(
                        {
                            "email": "pokemon@potato.io",
                            "first_name": "Konan",
                            "last_name": "Amegakure",
                            "phone": "123123123",
                            "field[18,0]": model.academy.slug,
                            "field[2,0]": "asdasd",
                        }
                    )
                ),
                call("FormEntry is considered a duplicate, no automations or tags added"),
            ],
        )
        self.assertEqual(logging.Logger.error.call_args_list, [])

        self.assertEqual(requests.get.call_args_list, [])
        self.assertEqual(requests.post.call_args_list, [])
        self.assertEqual(
            requests.request.call_args_list,
            [
                call(
                    "POST",
                    "https://old.hardcoded.breathecode.url/admin/api.php",
                    params=[
                        ("api_action", "contact_sync"),
                        ("api_key", model["active_campaign_academy"].ac_key),
                        ("api_output", "json"),
                    ],
                    data={
                        "email": "pokemon@potato.io",
                        "first_name": "Konan",
                        "last_name": "Amegakure",
                        "phone": "123123123",
                        "field[18,0]": model["academy"].slug,
                        "field[2,0]": "asdasd",
                    },
                    timeout=3,
                ),
            ],
        )
