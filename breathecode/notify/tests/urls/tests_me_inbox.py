from datetime import datetime

import capyc.pytest as capy
import pytest
from django.urls.base import reverse_lazy
from linked_services.django.actions import reset_app_cache
from rest_framework import status
from rest_framework.test import APIClient

from breathecode.notify.actions import send_inbox_notification


@pytest.fixture(autouse=True)
def setup(db):
    reset_app_cache()
    yield


def get_serializer(notification, data={}):
    return {
        "id": notification.id,
        "slug": notification.slug,
        "title": notification.title,
        "message": notification.message,
        "level": notification.level,
        "link": notification.link,
        "meta": notification.meta,
        "academy": None,
        "read_at": notification.read_at,
        "created_at": notification.created_at.isoformat().replace("+00:00", "Z"),
        **data,
    }


def test_no_auth(client: APIClient):
    for url in [reverse_lazy("notify:me_inbox"), reverse_lazy("notify:me_inbox_unread")]:
        response = client.get(url)

        assert response.json() == {"detail": "Authentication credentials were not provided.", "status_code": 401}
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_list_is_newest_first_and_does_not_mark_as_read(database: capy.Database, client: APIClient):
    model = database.create(user=1)
    first = send_inbox_notification(model.user, "plan-expired", "First", "Body", level="WARNING", link="/profile")
    second = send_inbox_notification(model.user, "plan-expired", "Second")
    client.force_authenticate(model.user)

    response = client.get(reverse_lazy("notify:me_inbox"))

    assert response.json() == [get_serializer(second), get_serializer(first)]
    assert response.status_code == status.HTTP_200_OK
    assert [x["read_at"] for x in database.list_of("notify.InboxNotification")] == [None, None]


def test_list_only_has_the_notifications_of_the_user(database: capy.Database, client: APIClient):
    model = database.create(user=2)
    mine = send_inbox_notification(model.user[0], "plan-expired", "Mine")
    send_inbox_notification(model.user[1], "plan-expired", "Not mine")
    client.force_authenticate(model.user[0])

    response = client.get(reverse_lazy("notify:me_inbox"))

    assert response.json() == [get_serializer(mine)]


def test_unread_filter_and_count(database: capy.Database, client: APIClient, utc_now: datetime):
    model = database.create(user=1)
    read = send_inbox_notification(model.user, "plan-expired", "Read")
    read.read_at = utc_now
    read.save()
    unread = send_inbox_notification(model.user, "plan-expired", "Unread")
    client.force_authenticate(model.user)

    response = client.get(reverse_lazy("notify:me_inbox") + "?unread=true")
    assert response.json() == [get_serializer(unread)]

    response = client.get(reverse_lazy("notify:me_inbox_unread"))
    assert response.json() == {"unread": 1}
    assert response.status_code == status.HTTP_200_OK


def test_mark_one_as_read(database: capy.Database, client: APIClient, utc_now: datetime):
    model = database.create(user=1)
    first = send_inbox_notification(model.user, "plan-expired", "First")
    second = send_inbox_notification(model.user, "plan-expired", "Second")
    client.force_authenticate(model.user)

    response = client.put(reverse_lazy("notify:me_inbox_id", kwargs={"notification_id": first.id}))

    assert response.json() == {"unread": 1}
    assert response.status_code == status.HTTP_200_OK
    assert [(x["id"], x["read_at"]) for x in database.list_of("notify.InboxNotification")] == [
        (first.id, utc_now),
        (second.id, None),
    ]


def test_mark_one_of_another_user_is_not_found(database: capy.Database, client: APIClient):
    model = database.create(user=2)
    other = send_inbox_notification(model.user[1], "plan-expired", "Not mine")
    client.force_authenticate(model.user[0])

    response = client.put(reverse_lazy("notify:me_inbox_id", kwargs={"notification_id": other.id}))

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert [x["read_at"] for x in database.list_of("notify.InboxNotification")] == [None]


def test_mark_all_as_read(database: capy.Database, client: APIClient, utc_now: datetime):
    model = database.create(user=2)
    send_inbox_notification(model.user[0], "plan-expired", "First")
    send_inbox_notification(model.user[0], "plan-expired", "Second")
    send_inbox_notification(model.user[1], "plan-expired", "Not mine")
    client.force_authenticate(model.user[0])

    response = client.put(reverse_lazy("notify:me_inbox"))

    assert response.json() == {"unread": 0}
    assert [x["read_at"] for x in database.list_of("notify.InboxNotification")] == [utc_now, utc_now, None]


def test_dedupe_key_keeps_one_per_slug_and_key(database: capy.Database):
    model = database.create(user=1)

    first = send_inbox_notification(model.user, "plan-expired", "First", dedupe_key="plan-financing-1")
    again = send_inbox_notification(model.user, "plan-expired", "Again", dedupe_key="plan-financing-1")
    other_slug = send_inbox_notification(model.user.id, "services-removed", "Other", dedupe_key="plan-financing-1")

    assert again.id == first.id
    assert other_slug.id != first.id
    assert [x["title"] for x in database.list_of("notify.InboxNotification")] == ["First", "Other"]


def test_send_does_not_raise_without_user(database: capy.Database):
    assert send_inbox_notification(None, "plan-expired", "Nobody") is None
    assert database.list_of("notify.InboxNotification") == []
