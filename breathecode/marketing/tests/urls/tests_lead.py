"""
Test /academy/lead
"""

from datetime import datetime
from decimal import Decimal
import re
import string
from random import choice, choices, randint
from unittest.mock import MagicMock, PropertyMock
from django.urls.base import reverse_lazy
import pytest
from rest_framework import status
from faker import Faker
from rest_framework.test import APIClient

from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode

fake = Faker()


def random_string():
    return "".join(choices(string.ascii_letters, k=10))


def post_serializer(data={}):
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
        "utm_placement": None,
        "utm_term": None,
        "utm_plan": None,
        "sex": None,
        "custom_fields": None,
        "referral_key": None,
        "gclid": None,
        "tags": "",
        "automations": "",
        "street_address": None,
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
        "ac_contact_id": None,
        "ac_deal_id": None,
        "ac_expected_cohort": None,
        "ac_deal_owner_id": None,
        "ac_deal_location": None,
        "ac_deal_course": None,
        "ac_deal_owner_full_name": None,
        "ac_expected_cohort_date": None,
        "ac_deal_amount": None,
        "ac_deal_currency_code": None,
        "won_at": None,
        "contact": None,
        "academy": None,
        "user": None,
        "lead_generation_app": None,
        **data,
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
        "utm_placement": None,
        "utm_term": None,
        "utm_plan": None,
        "sex": None,
        "custom_fields": None,
        "referral_key": None,
        "gclid": None,
        "tags": "",
        "automations": "",
        "street_address": None,
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
        "ac_contact_id": None,
        "ac_deal_id": None,
        "ac_expected_cohort": None,
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


def generate_form_entry_kwargs(data={}):
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
        "utm_url": fake.url(),
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
        "current_download": random_string(),
        **data,
    }


class FakeRecaptcha:

    class RiskAnalysis:

        def __init__(self, *args, **kwargs):
            self.score = 0.9

    def __init__(self, *args, **kwargs):
        self.risk_analysis = self.RiskAnalysis()


def assertDatetime(date: datetime) -> bool:
    if not isinstance(date, str):
        assert isinstance(date, datetime)
        return True

    try:
        string = re.sub(r"Z$", "", date)
        datetime.fromisoformat(string)
        return True
    except Exception:
        assert 0


@pytest.fixture(autouse=True)
def setup_db(db, monkeypatch):
    monkeypatch.setattr("breathecode.services.google_cloud.Recaptcha.__init__", lambda: None)
    monkeypatch.setattr(
        "breathecode.services.google_cloud.Recaptcha.create_assessment", MagicMock(return_value=FakeRecaptcha())
    )
    monkeypatch.setattr("uuid.UUID.int", PropertyMock(return_value=1000))
    yield


# When: Passing nothing
def test_lead__without_data(bc: Breathecode, client: APIClient):
    url = reverse_lazy("marketing:lead")

    response = client.post(url, format="json")
    json = response.json()

    assertDatetime(json["created_at"])
    assertDatetime(json["updated_at"])
    del json["created_at"]
    del json["updated_at"]

    expected = post_serializer(
        data={
            "attribution_id": None,
        }
    )

    assert json == expected
    assert response.status_code == status.HTTP_201_CREATED

    assert bc.database.list_of("marketing.FormEntry") == [
        form_entry_field(
            {
                "id": 1,
                "academy_id": None,
                "storage_status": "ERROR",
                "storage_status_text": "Missing location information",
                "attribution_id": None,
            }
        )
    ]


# When: Validations of fields
def test_lead__with__bad_data(bc: Breathecode, client: APIClient):
    url = reverse_lazy("marketing:lead")

    data = generate_form_entry_kwargs()
    response = client.post(url, data, format="json")

    json = response.json()
    expected = {
        "phone": ["Phone number must be entered in the format: '+99999999'. Up to 15 digits allowed."],
        "language": ["Ensure this field has no more than 2 characters."],
    }

    assert json == expected
    assert response.status_code == status.HTTP_400_BAD_REQUEST


# When: Passing required fields
def test_lead__with__data(bc: Breathecode, client: APIClient):
    url = reverse_lazy("marketing:lead")

    data = generate_form_entry_kwargs(
        {
            "phone": "123456789",
            "language": "en",
        }
    )

    response = client.post(url, data, format="json")
    json = response.json()

    assertDatetime(json["created_at"])
    assertDatetime(json["updated_at"])
    del json["created_at"]
    del json["updated_at"]

    expected = post_serializer(
        {
            **data,
            "id": 1,
            "academy": None,
            "latitude": bc.format.to_decimal_string(data["latitude"]),
            "longitude": bc.format.to_decimal_string(data["longitude"]),
            "attribution_id": "75b36c508866d18732305da14fe9a0",
        }
    )

    assert json == expected
    assert response.status_code == status.HTTP_201_CREATED
    assert bc.database.list_of("marketing.FormEntry") == [
        form_entry_field(
            {
                **data,
                "id": 1,
                "academy_id": None,
                "latitude": Decimal(data["latitude"]),
                "longitude": Decimal(data["longitude"]),
                "storage_status": "ERROR",
                "storage_status_text": f"No academy found with slug {data['location']}",
                "attribution_id": "75b36c508866d18732305da14fe9a0",
            }
        )
    ]


# When: Passing slug of Academy or AcademyAlias
@pytest.mark.parametrize(
    "academy,academy_alias,academy_id",
    [
        ({"slug": "midgard"}, None, None),
        ({"slug": "midgard"}, 1, None),
        (1, {"active_campaign_slug": "midgard"}, 1),
    ],
)
def test_passing_slug_of_academy_or_academy_alias(
    bc: Breathecode, client: APIClient, academy, academy_alias, academy_id
):
    model = bc.database.create(academy=academy, academy_alias=academy_alias, active_campaig_academy=1)
    url = reverse_lazy("marketing:lead")

    data = generate_form_entry_kwargs(
        {
            "phone": "123456789",
            "language": "en",
            "location": "midgard",
        }
    )

    response = client.post(url, data, format="json")
    json = response.json()

    assertDatetime(json["created_at"])
    assertDatetime(json["updated_at"])
    del json["created_at"]
    del json["updated_at"]

    expected = post_serializer(
        {
            **data,
            "id": model.academy.id,
            "academy": academy_id,
            "latitude": bc.format.to_decimal_string(data["latitude"]),
            "longitude": bc.format.to_decimal_string(data["longitude"]),
            "attribution_id": "75b36c508866d18732305da14fe9a0",
        }
    )

    assert json == expected
    assert response.status_code == status.HTTP_201_CREATED
    assert bc.database.list_of("marketing.FormEntry") == [
        form_entry_field(
            {
                **data,
                "id": model.academy.id,
                "academy_id": academy_id,
                "latitude": Decimal(data["latitude"]),
                "longitude": Decimal(data["longitude"]),
                "storage_status": "ERROR",
                "storage_status_text": "No academy found with slug midgard",
                "attribution_id": "75b36c508866d18732305da14fe9a0",
            }
        )
    ]
