from datetime import datetime, timedelta

import capyc.pytest as capy
import pytest
from django.urls.base import reverse_lazy
from linked_services.django.actions import reset_app_cache
from rest_framework import status
from rest_framework.test import APIClient


@pytest.fixture(autouse=True)
def setup(db):
    reset_app_cache()
    yield


def academy_serializer(academy):
    return {
        "id": academy.id,
        "name": academy.name,
        "slug": academy.slug,
    }


def get_serializer(notification, academy=None, data={}):
    academy_data = None
    if academy:
        academy_data = academy_serializer(academy)

    return {
        "academy": academy_data,
        "done_at": notification.done_at,
        "id": notification.id,
        "message": notification.message,
        "meta": notification.meta,
        "seen_at": notification.seen_at,
        "sent_at": notification.sent_at,
        "status": notification.status,
        "type": notification.type,
        **data,
    }


def test_no_auth(database: capy.Database, client: APIClient):
    url = reverse_lazy("notify:me_notification")
    response = client.get(url)

    json = response.json()
    expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}

    assert json == expected
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert database.list_of("notify.Notification") == []


def test_no_notifications(database: capy.Database, client: APIClient, format: capy.Format, utc_now: datetime):
    model = database.create(user=1)
    client.force_authenticate(model.user)

    url = reverse_lazy("notify:me_notification")
    response = client.get(url)

    json = response.json()
    expected = []

    assert json == expected
    assert response.status_code == status.HTTP_200_OK
    assert database.list_of("notify.Notification") == []


def test_two_notifications(database: capy.Database, client: APIClient, format: capy.Format, utc_now: datetime):
    model = database.create(user=1, notification=2)
    client.force_authenticate(model.user)

    url = reverse_lazy("notify:me_notification")
    response = client.get(url)

    json = response.json()
    expected = [
        get_serializer(model.notification[1], data={"seen_at": utc_now.isoformat().replace("+00:00", "Z")}),
        get_serializer(model.notification[0], data={"seen_at": utc_now.isoformat().replace("+00:00", "Z")}),
    ]
    assert json == expected
    assert response.status_code == status.HTTP_200_OK
    assert database.list_of("notify.Notification") == [
        {
            **format.to_obj_repr(model.notification[0]),
            "seen_at": utc_now,
        },
        {
            **format.to_obj_repr(model.notification[1]),
            "seen_at": utc_now,
        },
    ]


class TestDoneAt:

    def test_pending_next_5_minutes(
        self,
        database: capy.Database,
        client: APIClient,
        format: capy.Format,
        utc_now: datetime,
    ):
        model = database.create(user=1, notification=(2, {"done_at": utc_now + timedelta(minutes=5)}))
        client.force_authenticate(model.user)

        url = reverse_lazy("notify:me_notification") + "?done_at=" + utc_now.isoformat().replace("+00:00", "Z")
        response = client.get(url)

        json = response.json()
        expected = [
            get_serializer(
                model.notification[1],
                data={
                    "done_at": (utc_now + timedelta(minutes=5)).isoformat().replace("+00:00", "Z"),
                    "seen_at": utc_now.isoformat().replace("+00:00", "Z"),
                },
            ),
            get_serializer(
                model.notification[0],
                data={
                    "done_at": (utc_now + timedelta(minutes=5)).isoformat().replace("+00:00", "Z"),
                    "seen_at": utc_now.isoformat().replace("+00:00", "Z"),
                },
            ),
        ]
        assert json == expected
        assert response.status_code == status.HTTP_200_OK
        assert database.list_of("notify.Notification") == [
            {
                **format.to_obj_repr(model.notification[0]),
                "seen_at": utc_now,
            },
            {
                **format.to_obj_repr(model.notification[1]),
                "seen_at": utc_now,
            },
        ]

    def test_pending_next_5_minutes(
        self,
        database: capy.Database,
        client: APIClient,
        format: capy.Format,
        utc_now: datetime,
    ):
        model = database.create(user=1, notification=(2, {"done_at": utc_now + timedelta(minutes=5)}))
        client.force_authenticate(model.user)

        url = reverse_lazy("notify:me_notification") + "?done_at=" + utc_now.isoformat().replace("+00:00", "Z")
        response = client.get(url)

        json = response.json()
        expected = [
            get_serializer(
                model.notification[1],
                data={
                    "done_at": (utc_now + timedelta(minutes=5)).isoformat().replace("+00:00", "Z"),
                    "seen_at": utc_now.isoformat().replace("+00:00", "Z"),
                },
            ),
            get_serializer(
                model.notification[0],
                data={
                    "done_at": (utc_now + timedelta(minutes=5)).isoformat().replace("+00:00", "Z"),
                    "seen_at": utc_now.isoformat().replace("+00:00", "Z"),
                },
            ),
        ]
        assert json == expected
        assert response.status_code == status.HTTP_200_OK
        assert database.list_of("notify.Notification") == [
            {
                **format.to_obj_repr(model.notification[0]),
                "seen_at": utc_now,
            },
            {
                **format.to_obj_repr(model.notification[1]),
                "seen_at": utc_now,
            },
        ]


class TestSeen:

    def test_db_seen_at_eq_none__qs_seen_eq_true(
        self,
        database: capy.Database,
        client: APIClient,
        format: capy.Format,
    ):
        model = database.create(user=1, notification=(2, {"seen_at": None}))
        client.force_authenticate(model.user)

        url = reverse_lazy("notify:me_notification") + "?seen=true"
        response = client.get(url)

        json = response.json()
        expected = []
        assert json == expected
        assert response.status_code == status.HTTP_200_OK
        assert database.list_of("notify.Notification") == [
            {
                **format.to_obj_repr(model.notification[0]),
                "seen_at": None,
            },
            {
                **format.to_obj_repr(model.notification[1]),
                "seen_at": None,
            },
        ]

    def test_db_seen_at_not_none__qs_seen_eq_true(
        self,
        database: capy.Database,
        client: APIClient,
        format: capy.Format,
        utc_now: datetime,
    ):
        model = database.create(user=1, notification=(2, {"seen_at": utc_now}))
        client.force_authenticate(model.user)

        url = reverse_lazy("notify:me_notification") + "?seen=true"
        response = client.get(url)

        json = response.json()
        expected = [
            get_serializer(
                model.notification[1],
                data={
                    "seen_at": utc_now.isoformat().replace("+00:00", "Z"),
                },
            ),
            get_serializer(
                model.notification[0],
                data={
                    "seen_at": utc_now.isoformat().replace("+00:00", "Z"),
                },
            ),
        ]
        assert json == expected
        assert response.status_code == status.HTTP_200_OK
        assert database.list_of("notify.Notification") == [
            format.to_obj_repr(model.notification[0]),
            format.to_obj_repr(model.notification[1]),
        ]


class TestAcademy:

    def test_bad_academies(
        self,
        database: capy.Database,
        client: APIClient,
        format: capy.Format,
    ):
        model = database.create(
            user=1,
            notification=[{"academy_id": n + 1} for n in range(2)],
            academy=2,
            city=1,
            country=1,
        )
        client.force_authenticate(model.user)

        url = reverse_lazy("notify:me_notification") + "?academy=fake1,fake2"
        response = client.get(url)

        json = response.json()
        expected = []
        assert json == expected
        assert response.status_code == status.HTTP_200_OK
        assert database.list_of("notify.Notification") == [
            format.to_obj_repr(model.notification[0]),
            format.to_obj_repr(model.notification[1]),
        ]

    def test_with_academies(
        self,
        database: capy.Database,
        client: APIClient,
        format: capy.Format,
        utc_now: datetime,
    ):
        model = database.create(
            user=1,
            notification=[{"academy_id": n + 1} for n in range(2)],
            academy=2,
            city=1,
            country=1,
        )
        client.force_authenticate(model.user)

        url = reverse_lazy("notify:me_notification") + f"?academy={model.academy[0].slug},{model.academy[1].slug}"
        response = client.get(url)

        json = response.json()
        expected = [
            get_serializer(
                model.notification[1],
                academy=model.academy[1],
                data={
                    "seen_at": utc_now.isoformat().replace("+00:00", "Z"),
                },
            ),
            get_serializer(
                model.notification[0],
                academy=model.academy[0],
                data={
                    "seen_at": utc_now.isoformat().replace("+00:00", "Z"),
                },
            ),
        ]

        assert json == expected
        assert response.status_code == status.HTTP_200_OK
        assert database.list_of("notify.Notification") == [
            {
                **format.to_obj_repr(model.notification[0]),
                "seen_at": utc_now,
            },
            {
                **format.to_obj_repr(model.notification[1]),
                "seen_at": utc_now,
            },
        ]
