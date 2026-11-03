"""
Test /v2/marketing/lead and /v2/marketing/lead-captcha
"""

from unittest.mock import MagicMock

import pytest
from django.urls.base import reverse_lazy
from rest_framework import status
from rest_framework.test import APIClient

from breathecode.marketing import tasks
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode


@pytest.fixture(autouse=True)
def setup(db, monkeypatch):
    monkeypatch.setattr(tasks.persist_single_lead, "delay", MagicMock())
    yield


@pytest.mark.parametrize("url_name", ["v2:marketing:lead_v2", "v2:marketing:lead_captcha_v2"])
def test_ppc_tracking_id_is_forwarded_as_gclid_to_persist_single_lead(
    bc: Breathecode, client: APIClient, url_name
):
    url = reverse_lazy(url_name)
    data = {
        "first_name": "Rene",
        "last_name": "Descartes",
        "email": "rene@descartes.com",
        "phone": "123456789",
        "language": "en",
        "ppc_tracking_id": "CjwKCAjwoOjVBhArEiwAUwDak8_BwE",
    }

    response = client.post(url, data, format="json")
    json = response.json()

    assert response.status_code == status.HTTP_201_CREATED
    assert json["ppc_tracking_id"] == data["ppc_tracking_id"]
    assert "gclid" not in json

    assert bc.database.list_of("marketing.FormEntry")[0]["gclid"] == data["ppc_tracking_id"]

    assert tasks.persist_single_lead.delay.call_count == 1
    form_entry = tasks.persist_single_lead.delay.call_args.args[0]
    assert form_entry["gclid"] == data["ppc_tracking_id"]


@pytest.mark.parametrize("url_name", ["v2:marketing:lead_v2", "v2:marketing:lead_captcha_v2"])
def test_without_ppc_tracking_id(bc: Breathecode, client: APIClient, url_name):
    url = reverse_lazy(url_name)
    data = {
        "first_name": "Rene",
        "last_name": "Descartes",
        "email": "rene@descartes.com",
        "phone": "123456789",
        "language": "en",
    }

    response = client.post(url, data, format="json")
    json = response.json()

    assert response.status_code == status.HTTP_201_CREATED
    assert json["ppc_tracking_id"] is None

    form_entry = tasks.persist_single_lead.delay.call_args.args[0]
    assert form_entry["gclid"] is None
