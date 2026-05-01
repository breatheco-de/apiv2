from unittest.mock import MagicMock

import pytest
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.urls.base import reverse_lazy
from rest_framework import status
from rest_framework.test import APIClient

from breathecode.assignments.models import IGNORED, LearnPackWebhook
from breathecode.authenticate.models import Capability
from breathecode.services.learnpack.webhook_ignore import LEARNPACK_FEATURES_TELEMETRY_WEBHOOK_IGNORE_KEY
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode


@pytest.fixture
def client():
    return APIClient()


def test_get_returns_telemetry_ignore_subset(db: None, bc: Breathecode, client: APIClient):
    model = bc.database.create(
        user=1,
        country=1,
        city=1,
        academy=1,
        profile_academy=1,
        role=1,
        capability="read_assignment",
        academy_auth_settings=1,
    )
    s = model.academy_auth_settings
    s.learnpack_features = {LEARNPACK_FEATURES_TELEMETRY_WEBHOOK_IGNORE_KEY: {"user_ids": [9]}}
    s.save(update_fields=["learnpack_features"])
    client.force_authenticate(model.user)
    url = reverse_lazy("assignments:academy_learnpack_telemetry_webhook_ignore")
    response = client.get(url, headers={"Academy": str(model.academy.id)})

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"user_ids": [9]}


def test_put_replaces_ignore_config(db: None, bc: Breathecode, client: APIClient):
    model = bc.database.create(
        user=1,
        country=1,
        city=1,
        academy=1,
        profile_academy=1,
        role=1,
        capability="read_assignment",
        academy_auth_settings=1,
    )
    crud, _ = Capability.objects.get_or_create(
        slug="crud_telemetry",
        defaults={"description": "crud_telemetry"},
    )
    model.role.capabilities.add(crud)

    client.force_authenticate(model.user)
    url = reverse_lazy("assignments:academy_learnpack_telemetry_webhook_ignore")
    body = {"user_ids": [3], "learnpack_package_ids": [100]}
    response = client.put(url, data=body, format="json", headers={"Academy": str(model.academy.id)})

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == body
    model.academy_auth_settings.refresh_from_db()
    lf = model.academy_auth_settings.learnpack_features
    assert lf[LEARNPACK_FEATURES_TELEMETRY_WEBHOOK_IGNORE_KEY] == body


def test_me_telemetry_skips_celery_when_user_matches_ignore(monkeypatch, db: None, bc: Breathecode, client: APIClient):
    delay = MagicMock()
    monkeypatch.setattr("breathecode.assignments.tasks.async_learnpack_webhook.delay", delay)

    model = bc.database.create(user=1, country=1, city=1, academy=1, academy_auth_settings=1)
    uid = model.user.id
    settings = model.academy_auth_settings
    settings.learnpack_features = {
        LEARNPACK_FEATURES_TELEMETRY_WEBHOOK_IGNORE_KEY: {"user_ids": [uid]}
    }
    settings.save(update_fields=["learnpack_features"])

    ct = ContentType.objects.get_for_model(type(model.user))
    perm = Permission.objects.filter(codename="upload_assignment_telemetry", content_type=ct).first()
    if perm is None:
        perm = Permission.objects.create(
            codename="upload_assignment_telemetry",
            name="upload_assignment_telemetry",
            content_type=ct,
        )
    model.user.user_permissions.add(perm)
    client.force_authenticate(model.user)

    url = reverse_lazy("assignments:me_telemetry")
    payload = {"event": "open_step", "user_id": uid, "slug": "some-exercise-slug"}
    response = client.post(
        url,
        data=payload,
        format="json",
        headers={"Academy": str(model.academy.id)},
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.content.decode().strip().strip('"')
    assert body == "ok"
    delay.assert_not_called()
    row = LearnPackWebhook.objects.order_by("-id").first()
    assert row is not None
    assert row.status == IGNORED
    assert row.status_text and "telemetry_webhook_ignore" in row.status_text
