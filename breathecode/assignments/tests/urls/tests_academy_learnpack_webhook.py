from django.urls.base import reverse_lazy
from rest_framework import status
from rest_framework.test import APIClient

from breathecode.assignments.models import ERROR, LearnPackWebhook
from breathecode.authenticate.models import Capability
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode


def _result_items(response_json):
    if isinstance(response_json, dict) and "results" in response_json:
        return response_json["results"]
    return response_json


def test_list_learnpack_webhooks_filters_by_multi_values(db: None, bc: Breathecode, client: APIClient):
    model = bc.database.create(user=1, profile_academy=1, role=1, capability="read_assignment")
    client.force_authenticate(model.user)
    student_1 = model.user

    LearnPackWebhook.objects.create(
        is_streaming=True,
        event="batch",
        asset_id=10,
        learnpack_package_id=1000,
        payload={"asset_id": 10, "package_id": 1000},
        student=student_1,
        status="PENDING",
    )
    LearnPackWebhook.objects.create(
        is_streaming=True,
        event="open_step",
        asset_id=20,
        learnpack_package_id=2000,
        payload={"asset_id": 20, "package_id": 2000},
        student=student_1,
        status="DONE",
    )

    url = (
        reverse_lazy("assignments:academy_learnpack_webhook")
        + f"?student={student_1.id},999&event=batch,open_step&asset_id=10,20&learnpack_package_id=1000,2000"
    )
    response = client.get(url, headers={"Academy": 1})
    data = response.json()
    items = _result_items(data)

    assert response.status_code == status.HTTP_200_OK
    assert len(items) == 2
    assert {x["event"] for x in items} == {"batch", "open_step"}


def test_list_learnpack_webhooks_rejects_invalid_numeric_filter(db: None, bc: Breathecode, client: APIClient):
    model = bc.database.create(user=1, profile_academy=1, role=1, capability="read_assignment")
    client.force_authenticate(model.user)

    url = reverse_lazy("assignments:academy_learnpack_webhook") + "?asset_id=abc,1"
    response = client.get(url, headers={"Academy": 1})
    data = response.json()

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert data["detail"] == "invalid-filter"


def test_delete_learnpack_webhook_requires_auth(db: None, bc: Breathecode, client: APIClient):
    model = bc.database.create(user=1, profile_academy=1, role=1, capability="read_assignment")
    row = LearnPackWebhook.objects.create(
        is_streaming=True,
        event="batch",
        asset_id=10,
        learnpack_package_id=1000,
        payload={"asset_id": 10, "package_id": 1000},
        student=model.user,
        status=ERROR,
    )

    url = reverse_lazy("assignments:academy_learnpack_webhook_id", kwargs={"webhook_id": row.id})
    response = client.delete(url, headers={"Academy": str(model.academy.id)})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_delete_learnpack_webhook_requires_crud_telemetry(db: None, bc: Breathecode, client: APIClient):
    model = bc.database.create(user=1, profile_academy=1, role=1, capability="read_assignment")
    client.force_authenticate(model.user)
    row = LearnPackWebhook.objects.create(
        is_streaming=True,
        event="batch",
        asset_id=11,
        learnpack_package_id=1001,
        payload={"asset_id": 11, "package_id": 1001},
        student=model.user,
        status=ERROR,
    )

    url = reverse_lazy("assignments:academy_learnpack_webhook_id", kwargs={"webhook_id": row.id})
    response = client.delete(url, headers={"Academy": str(model.academy.id)})

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_delete_learnpack_webhook_deletes_single_error_row(db: None, bc: Breathecode, client: APIClient):
    model = bc.database.create(user=1, profile_academy=1, role=1, capability="read_assignment")
    crud, _ = Capability.objects.get_or_create(slug="crud_telemetry", defaults={"description": "crud_telemetry"})
    model.role.capabilities.add(crud)
    client.force_authenticate(model.user)

    row = LearnPackWebhook.objects.create(
        is_streaming=True,
        event="batch",
        asset_id=12,
        learnpack_package_id=1002,
        payload={"asset_id": 12, "package_id": 1002},
        student=model.user,
        status=ERROR,
    )

    url = reverse_lazy("assignments:academy_learnpack_webhook_id", kwargs={"webhook_id": row.id})
    response = client.delete(url, headers={"Academy": str(model.academy.id)})

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert LearnPackWebhook.objects.filter(id=row.id).exists() is False


def test_delete_learnpack_webhook_rejects_non_error_status(db: None, bc: Breathecode, client: APIClient):
    model = bc.database.create(user=1, profile_academy=1, role=1, capability="read_assignment")
    crud, _ = Capability.objects.get_or_create(slug="crud_telemetry", defaults={"description": "crud_telemetry"})
    model.role.capabilities.add(crud)
    client.force_authenticate(model.user)

    row = LearnPackWebhook.objects.create(
        is_streaming=True,
        event="batch",
        asset_id=13,
        learnpack_package_id=1003,
        payload={"asset_id": 13, "package_id": 1003},
        student=model.user,
        status="DONE",
    )

    url = reverse_lazy("assignments:academy_learnpack_webhook_id", kwargs={"webhook_id": row.id})
    response = client.delete(url, headers={"Academy": str(model.academy.id)})

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "invalid-webhook-status"
    assert LearnPackWebhook.objects.filter(id=row.id).exists() is True


def test_delete_learnpack_webhook_not_found(db: None, bc: Breathecode, client: APIClient):
    model = bc.database.create(user=1, profile_academy=1, role=1, capability="read_assignment")
    crud, _ = Capability.objects.get_or_create(slug="crud_telemetry", defaults={"description": "crud_telemetry"})
    model.role.capabilities.add(crud)
    client.force_authenticate(model.user)

    url = reverse_lazy("assignments:academy_learnpack_webhook_id", kwargs={"webhook_id": 999999})
    response = client.delete(url, headers={"Academy": str(model.academy.id)})

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "webhook-not-found"


def test_bulk_delete_learnpack_webhook_requires_error_status(db: None, bc: Breathecode, client: APIClient):
    model = bc.database.create(user=1, profile_academy=1, role=1, capability="read_assignment")
    crud, _ = Capability.objects.get_or_create(slug="crud_telemetry", defaults={"description": "crud_telemetry"})
    model.role.capabilities.add(crud)
    client.force_authenticate(model.user)
    LearnPackWebhook.objects.create(
        is_streaming=True,
        event="batch",
        asset_id=14,
        learnpack_package_id=1004,
        payload={"asset_id": 14, "package_id": 1004},
        student=model.user,
        status=ERROR,
    )

    url = reverse_lazy("assignments:academy_learnpack_webhook")
    missing = client.delete(url, headers={"Academy": str(model.academy.id)})
    invalid = client.delete(f"{url}?status=DONE", headers={"Academy": str(model.academy.id)})

    assert missing.status_code == status.HTTP_400_BAD_REQUEST
    assert missing.json()["detail"] == "missing-status"
    assert invalid.status_code == status.HTTP_400_BAD_REQUEST
    assert invalid.json()["detail"] == "invalid-status"


def test_bulk_delete_learnpack_webhook_deletes_only_matching_error_rows(db: None, bc: Breathecode, client: APIClient):
    model = bc.database.create(user=1, profile_academy=1, role=1, capability="read_assignment")
    crud, _ = Capability.objects.get_or_create(slug="crud_telemetry", defaults={"description": "crud_telemetry"})
    model.role.capabilities.add(crud)
    client.force_authenticate(model.user)

    deletable = LearnPackWebhook.objects.create(
        is_streaming=True,
        event="batch",
        asset_id=20,
        learnpack_package_id=3000,
        payload={"asset_id": 20, "package_id": 3000},
        student=model.user,
        status=ERROR,
    )
    keep_other_asset = LearnPackWebhook.objects.create(
        is_streaming=True,
        event="batch",
        asset_id=21,
        learnpack_package_id=3000,
        payload={"asset_id": 21, "package_id": 3000},
        student=model.user,
        status=ERROR,
    )
    keep_other_status = LearnPackWebhook.objects.create(
        is_streaming=True,
        event="batch",
        asset_id=20,
        learnpack_package_id=3000,
        payload={"asset_id": 20, "package_id": 3000},
        student=model.user,
        status="DONE",
    )

    url = reverse_lazy("assignments:academy_learnpack_webhook")
    response = client.delete(
        f"{url}?status=ERROR&asset_id=20&learnpack_package_id=3000",
        headers={"Academy": str(model.academy.id)},
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert LearnPackWebhook.objects.filter(id=deletable.id).exists() is False
    assert LearnPackWebhook.objects.filter(id=keep_other_asset.id).exists() is True
    assert LearnPackWebhook.objects.filter(id=keep_other_status.id).exists() is True
