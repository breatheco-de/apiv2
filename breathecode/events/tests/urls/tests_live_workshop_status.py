from datetime import timedelta
from unittest.mock import MagicMock, patch

import capyc.pytest as capy
import pytest
from django.core.cache import cache
from django.urls.base import reverse_lazy
from django.utils import timezone

from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode

UTC_NOW = timezone.now()


@pytest.fixture(autouse=True)
def setup(db):
    cache.clear()
    yield


@patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
def test_anonymous_sees_live_event(bc: Breathecode, client: capy.Client):
    model = bc.database.create(
        event={
            "status": "ACTIVE",
            "starting_at": UTC_NOW - timedelta(minutes=10),
            "ending_at": UTC_NOW + timedelta(hours=1),
            "slug": "live-open",
            "title": "Open Live",
            "lang": "es",
        },
        event_type={"icon_url": bc.fake.url()},
    )

    url = reverse_lazy("events:live_workshop_status")
    response = client.get(url)

    assert response.status_code == 200
    assert response.json()["slug"] == model.event.slug


@patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
def test_auth_user_with_denied_plan_gets_null(bc: Breathecode, client: capy.Client):
    model = bc.database.create(
        user=1,
        token=1,
        event={
            "status": "ACTIVE",
            "starting_at": UTC_NOW - timedelta(minutes=10),
            "ending_at": UTC_NOW + timedelta(hours=1),
            "slug": "live-blocked",
            "title": "Blocked Live",
            "lang": "es",
        },
        event_type={"icon_url": bc.fake.url()},
        plan={"slug": "ai-engineering-core"},
        subscription={"status": "ACTIVE"},
    )
    model.event.denied_plans.add(model.plan)
    model.subscription.plans.add(model.plan)

    url = reverse_lazy("events:live_workshop_status")
    response = client.get(url, HTTP_AUTHORIZATION=f"Token {model.token.key}")

    assert response.status_code == 200
    # DRF may serialize None as empty body or JSON null
    if response.get("Content-Type"):
        assert response.json() is None
    else:
        assert response.content in (b"", b"null")


@patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
def test_auth_user_with_denied_plan_sees_other_live_event(bc: Breathecode, client: capy.Client):
    model = bc.database.create(
        user=1,
        token=1,
        event=[
            {
                "status": "ACTIVE",
                "starting_at": UTC_NOW - timedelta(minutes=20),
                "ending_at": UTC_NOW + timedelta(hours=1),
                "slug": "live-blocked",
                "title": "Blocked Live",
                "lang": "es",
            },
            {
                "status": "ACTIVE",
                "starting_at": UTC_NOW - timedelta(minutes=5),
                "ending_at": UTC_NOW + timedelta(hours=1),
                "slug": "live-allowed",
                "title": "Allowed Live",
                "lang": "es",
            },
        ],
        event_type={"icon_url": bc.fake.url()},
        plan={"slug": "ai-engineering-core"},
        subscription={"status": "ACTIVE"},
    )
    blocked, allowed = model.event
    blocked.denied_plans.add(model.plan)
    model.subscription.plans.add(model.plan)

    url = reverse_lazy("events:live_workshop_status")
    response = client.get(url, HTTP_AUTHORIZATION=f"Token {model.token.key}")

    assert response.status_code == 200
    assert response.json()["slug"] == allowed.slug
