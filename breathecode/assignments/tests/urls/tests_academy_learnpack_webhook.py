from django.urls.base import reverse_lazy
from rest_framework import status
from rest_framework.test import APIClient

from breathecode.assignments.models import LearnPackWebhook
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
