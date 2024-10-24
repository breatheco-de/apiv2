"""
Test /v1/auth/subscribe
"""

import base64
import hashlib
import hmac
import os
from unittest.mock import MagicMock, call

import capyc.pytest as capy
import pytest
from django.urls.base import reverse_lazy
from django.utils import timezone
from rest_framework import status

from breathecode.payments.tasks import process_google_webhook

now = timezone.now()


@pytest.fixture(autouse=True)
def setup(monkeypatch: pytest.MonkeyPatch, db):
    monkeypatch.setenv("GOOGLE_WEBHOOK_SECRET", "123456")

    yield


def test_no_data(database: capy.Database, client: capy.Client):
    url = reverse_lazy("authenticate:google_token", kwargs={"token": "78c9c2defd3be7f3f5b3ddd542ade55a2d35281b"})
    response = client.get(url, format="json")

    json = response.json()
    expected = {"detail": "no-callback-url", "status_code": 400}

    assert json == expected
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert database.list_of("authenticate.GoogleWebhook") == []


def test_not_authorized_event(database: capy.Database, client: capy.Client):

    url = reverse_lazy("authenticate:google_webhook")
    data = {}
    response = client.post(url, data=data, format="json")

    json = response.json()
    expected = {"detail": "invalid-webhook-data", "status_code": 400}

    assert json == expected
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert database.list_of("authenticate.GoogleWebhook") == []


def test_invalid_signature(database: capy.Database, client: capy.Client):
    url = reverse_lazy("authenticate:google_webhook")
    data = {
        "data": "invalid-data",
        "signature": "invalid-signature",
    }
    response = client.post(url, data=data, format="json")

    json = response.json()
    expected = {"detail": "invalid-signature", "status_code": 400}

    assert json == expected
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert database.list_of("authenticate.GoogleWebhook") == []


def test_authorized_event(database: capy.Database, client: capy.Client):
    message = base64.b64encode(b'{"credential_id": "123456"}').decode("utf-8")
    signature = hmac.new(
        key=os.getenv("GOOGLE_WEBHOOK_SECRET").encode("utf-8"), msg=message.encode("utf-8"), digestmod=hashlib.sha256
    ).hexdigest()
    url = reverse_lazy("authenticate:google_webhook")
    data = {
        "data": message,
        "signature": signature,
    }
    response = client.post(url, data=data, format="json")

    assert response.status_code == status.HTTP_202_ACCEPTED
    assert database.list_of("authenticate.GoogleWebhook") == [
        {
            "id": 1,
            "message": message,
            "status": "PENDING",
            "status_text": "",
            "type": "noSet",
        },
    ]
