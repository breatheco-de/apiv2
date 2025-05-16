import random
from datetime import timedelta

import capyc.pytest as capy
import pytest
from django.urls import reverse_lazy
from rest_framework import status

from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode


@pytest.fixture(autouse=True)
def setup(db, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "breathecode.payments.tasks.end_the_consumption_session.apply_async", lambda *args, **kwargs: None
    )
    yield


def db_item(service, data={}):
    return {
        "consumable_id": 1,
        "duration": None,
        "eta": None,
        "how_many": 1.0,
        "id": 1,
        "operation_code": "unsafe-consume-service-set",
        "path": "",
        "related_id": 0,
        "related_slug": "",
        "request": {
            "args": [],
            "headers": {
                "academy": None,
            },
            "kwargs": {
                "service_slug": service.slug,
            },
            "user": 1,
        },
        "status": "PENDING",
        "user_id": 1,
        "was_discounted": False,
        **data,
    }


def get_serializer(consumption_session, data={}):
    return {
        "id": consumption_session.id,
        "operation_code": consumption_session.operation_code,
        "eta": ...,
        "duration": ...,
        "how_many": consumption_session.how_many,
        "status": consumption_session.status,
        "was_discounted": consumption_session.was_discounted,
        "request": consumption_session.request,
        "path": consumption_session.path,
        "related_id": consumption_session.related_id,
        "related_slug": consumption_session.related_slug,
        "user": {
            "email": consumption_session.user.email,
            "first_name": consumption_session.user.first_name,
            "last_name": consumption_session.user.last_name,
        },
        **data,
    }


def random_duration():
    hours = random.randint(0, 23)
    minutes = random.randint(0, 59)
    seconds = random.randint(0, 59)
    return timedelta(hours=hours, minutes=minutes, seconds=seconds)


def test_get_no_auth(bc: Breathecode, client: capy.Client):
    url = reverse_lazy("payments:me_service_slug_consumptionsession", kwargs={"service_slug": "my-service"})
    response = client.get(url)

    json = response.json()
    expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}

    assert json == expected
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_service_not_found(bc: Breathecode, client: capy.Client):
    model = bc.database.create(user=1)
    client.force_authenticate(user=model.user)

    url = reverse_lazy("payments:me_service_slug_consumptionsession", kwargs={"service_slug": "bad-service"})
    response = client.get(url)

    json = response.json()
    expected = {"detail": "service-not-found", "status_code": 404}

    assert json == expected
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_get_empty_list(bc: Breathecode, client: capy.Client):
    model = bc.database.create(user=1, service=1)
    client.force_authenticate(user=model.user)

    url = reverse_lazy("payments:me_service_slug_consumptionsession", kwargs={"service_slug": model.service.slug})
    response = client.get(url)

    json = response.json()
    expected = []

    assert json == expected
    assert response.status_code == status.HTTP_200_OK


def test_get_one_session(bc: Breathecode, client: capy.Client, utc_now):
    duration = random_duration()
    model = bc.database.create(
        user=1,
        consumable=1,
        service={
            "session_duration": duration,
            "type": "VOID",
        },
        consumption_session={
            "how_many": 1,
            "eta": utc_now + duration,
            "duration": duration,
            "was_discounted": False,
            "operation_code": "unsafe-consume-service-set",
            "status": "PENDING",
            "path": "payments.Service",
        },
    )
    client.force_authenticate(user=model.user)

    url = reverse_lazy("payments:me_service_slug_consumptionsession", kwargs={"service_slug": model.service.slug})
    response = client.get(url)

    json = response.json()
    expected = [
        get_serializer(
            model.consumption_session,
            data={
                "duration": str(duration.total_seconds()),
                "eta": (utc_now + duration).isoformat().replace("+00:00", "Z"),
            },
        )
    ]

    assert json == expected
    assert response.status_code == status.HTTP_200_OK


def test_get_filter_by_status(bc: Breathecode, client: capy.Client, utc_now):
    duration = random_duration()
    model = bc.database.create(
        user=1,
        consumable=1,
        service={
            "session_duration": duration,
            "type": "VOID",
        },
        consumption_session=[
            {
                "how_many": 1,
                "eta": utc_now + duration,
                "duration": duration,
                "was_discounted": False,
                "operation_code": "unsafe-consume-service-set",
                "status": "PENDING",
                "path": "payments.Service",
            },
            {
                "how_many": 1,
                "eta": utc_now + duration,
                "duration": duration,
                "was_discounted": False,
                "operation_code": "unsafe-consume-service-set",
                "status": "DONE",
                "path": "payments.Service",
            },
        ],
    )
    client.force_authenticate(user=model.user)

    url = reverse_lazy("payments:me_service_slug_consumptionsession", kwargs={"service_slug": model.service.slug})
    response = client.get(f"{url}?status=DONE")

    json = response.json()
    expected = [
        get_serializer(
            model.consumption_session[1],
            data={
                "duration": str(duration.total_seconds()),
                "eta": (utc_now + duration).isoformat().replace("+00:00", "Z"),
            },
        )
    ]

    assert json == expected
    assert response.status_code == status.HTTP_200_OK


def test_no_auth(bc: Breathecode, client: capy.Client):
    url = reverse_lazy("payments:me_service_slug_consumptionsession", kwargs={"service_slug": "my-service"})

    response = client.put(url)

    json = response.json()
    expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}

    assert json == expected
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert bc.database.list_of("payments.ConsumptionSession") == []


def test_no_consumables(bc: Breathecode, client: capy.Client):
    url = reverse_lazy("payments:me_service_slug_consumptionsession", kwargs={"service_slug": "my-service"})

    model = bc.database.create(user=1)
    client.force_authenticate(user=model.user)

    response = client.put(url)

    json = response.json()
    expected = {"detail": "insufficient-credits", "status_code": 402}

    assert json == expected
    assert response.status_code == status.HTTP_402_PAYMENT_REQUIRED
    assert bc.database.list_of("payments.ConsumptionSession") == []


def test_created(bc: Breathecode, client: capy.Client, utc_now):
    duration = random_duration()
    model = bc.database.create(user=1, consumable=1, service={"session_duration": duration, "type": "VOID"})
    url = reverse_lazy("payments:me_service_slug_consumptionsession", kwargs={"service_slug": model.service.slug})

    client.force_authenticate(user=model.user)

    response = client.put(url)

    json = response.json()
    expected = {"id": 1, "status": "ok"}

    assert json == expected
    assert response.status_code == status.HTTP_201_CREATED
    assert bc.database.list_of("payments.ConsumptionSession") == [
        db_item(
            model.service,
            data={
                "related_id": 1,
                "related_slug": model.service.slug,
                "path": "payments.Service",
                "duration": duration,
                "eta": utc_now + duration,
            },
        )
    ]


def test_cached(bc: Breathecode, client: capy.Client, utc_now, fake):
    slug = fake.slug()
    duration = random_duration()
    model = bc.database.create(
        user=1,
        consumable=1,
        service={
            "session_duration": duration,
            "slug": slug,
            "type": "VOID",
        },
        consumption_session={
            "how_many": 1,
            "eta": utc_now + duration,
            "duration": duration,
            "was_discounted": False,
            "operation_code": "unsafe-consume-service-set",
            "related_id": 1,
            "related_slug": slug,
            "status": "PENDING",
            "path": "payments.Service",
            "request": {
                "args": [],
                "headers": {
                    "academy": None,
                },
                "kwargs": {
                    "service_slug": slug,
                },
                "user": 1,
            },
        },
    )
    url = reverse_lazy("payments:me_service_slug_consumptionsession", kwargs={"service_slug": model.service.slug})

    client.force_authenticate(user=model.user)

    response = client.put(url)

    json = response.json()
    expected = {"id": 2, "status": "ok"}

    assert json == expected
    assert response.status_code == status.HTTP_201_CREATED
    assert bc.database.list_of("payments.ConsumptionSession") == [
        db_item(
            model.service,
            data={
                "id": 1,
                "related_id": 1,
                "related_slug": model.service.slug,
                "path": "payments.Service",
                "duration": duration,
                "eta": utc_now + duration,
            },
        ),
        db_item(
            model.service,
            data={
                "id": 2,
                "related_id": 1,
                "related_slug": model.service.slug,
                "path": "payments.Service",
                "duration": duration,
                "eta": utc_now + duration,
            },
        ),
    ]
