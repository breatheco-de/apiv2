from datetime import timedelta

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from breathecode.events.actions import (
    backfill_checkins_for_new_group_event,
    canonical_group_event,
    register_to_event_or_group,
)
from breathecode.events.models import EventCheckin

GROUP = "python-intensive"


@pytest.fixture(autouse=True)
def setup(db):
    yield


def _future_range(days=1, hours=2):
    start = timezone.now() + timedelta(days=days)
    return start, start + timedelta(hours=hours)


def _event_kwargs(title, starting_at, ending_at, status="ACTIVE"):
    return {
        "title": title,
        "starting_at": starting_at,
        "ending_at": ending_at,
        "status": status,
        "lang": "en",
        "is_public": True,
        "capacity": 10,
        "banner": "https://example.com/b.png",
        "tags": "workshop",
        "event_group": GROUP,
    }


def test_register_fanout_creates_pending_for_upcoming_sessions(database):
    start1, end1 = _future_range(1)
    start2, end2 = _future_range(2)
    start3, end3 = _future_range(3)

    model = database.create(
        academy=1,
        city=1,
        country=1,
        event_type={"lang": "en", "description": "Workshop type"},
        event=[
            _event_kwargs("Day 1", start1, end1),
            _event_kwargs("Day 2", start2, end2),
            _event_kwargs("Day 3", start3, end3),
        ],
    )

    for event in model.event:
        event.event_type = model.event_type
        event.academy = model.academy
        event.save()

    checkin, already = register_to_event_or_group(
        {
            "event": model.event[0],
            "email": "student@example.com",
            "first_name": "Stu",
            "last_name": "Dent",
        }
    )

    assert already is False
    assert checkin is not None
    assert checkin.event_id == model.event[0].id
    assert checkin.first_name == "Stu"
    assert checkin.last_name == "Dent"
    assert EventCheckin.objects.filter(email="student@example.com").count() == 3
    assert EventCheckin.objects.filter(email="student@example.com", status="PENDING").count() == 3


def test_register_skips_past_sessions(database):
    past_start = timezone.now() - timedelta(days=2)
    past_end = timezone.now() - timedelta(days=2) + timedelta(hours=2)
    start2, end2 = _future_range(1)

    model = database.create(
        academy=1,
        city=1,
        country=1,
        event_type={"lang": "en", "description": "Workshop type"},
        event=[
            _event_kwargs("Past", past_start, past_end, status="FINISHED"),
            _event_kwargs("Future", start2, end2),
        ],
    )

    for event in model.event:
        event.event_type = model.event_type
        event.academy = model.academy
        event.save()

    register_to_event_or_group({"event": model.event[1], "email": "late@example.com"})

    assert EventCheckin.objects.filter(email="late@example.com").count() == 1
    assert EventCheckin.objects.filter(email="late@example.com", event=model.event[1]).exists()
    assert not EventCheckin.objects.filter(email="late@example.com", event=model.event[0]).exists()


def test_register_ended_event_only_that_day(database):
    past_start = timezone.now() - timedelta(days=1)
    past_end = timezone.now() - timedelta(hours=1)
    start2, end2 = _future_range(1)

    model = database.create(
        academy=1,
        city=1,
        country=1,
        event_type={"lang": "en", "description": "Workshop type"},
        event=[
            _event_kwargs("Past", past_start, past_end, status="FINISHED"),
            _event_kwargs("Future", start2, end2),
        ],
    )

    for event in model.event:
        event.event_type = model.event_type
        event.academy = model.academy
        event.save()

    register_to_event_or_group({"event": model.event[0], "email": "past@example.com"})

    assert EventCheckin.objects.filter(email="past@example.com").count() == 1
    assert EventCheckin.objects.filter(email="past@example.com", event=model.event[0]).exists()


def test_second_register_fills_missing_days(database):
    start1, end1 = _future_range(1)
    start2, end2 = _future_range(2)

    model = database.create(
        academy=1,
        city=1,
        country=1,
        event_type={"lang": "en", "description": "Workshop type"},
        event=[
            _event_kwargs("Day 1", start1, end1),
            _event_kwargs("Day 2", start2, end2),
        ],
    )

    for event in model.event:
        event.event_type = model.event_type
        event.academy = model.academy
        event.save()

    EventCheckin.objects.create(event=model.event[0], email="partial@example.com", status="PENDING")

    _, already = register_to_event_or_group(
        {
            "event": model.event[0],
            "email": "partial@example.com",
        }
    )

    assert already is False
    assert EventCheckin.objects.filter(email="partial@example.com").count() == 2


def test_backfill_new_group_event(database):
    start1, end1 = _future_range(1)
    start2, end2 = _future_range(2)

    model = database.create(
        academy=1,
        city=1,
        country=1,
        event_type={"lang": "en", "description": "Workshop type"},
        event=_event_kwargs("Day 1", start1, end1),
    )

    model.event.event_type = model.event_type
    model.event.academy = model.academy
    model.event.save()

    EventCheckin.objects.create(event=model.event, email="member@example.com", status="PENDING")

    day2 = database.create(
        event={
            **_event_kwargs("Day 2", start2, end2),
            "academy": model.academy,
            "event_type": model.event_type,
        }
    ).event
    day2.save()

    backfill_checkins_for_new_group_event(day2)

    assert EventCheckin.objects.filter(email="member@example.com", event=day2).exists()


def test_canonical_group_event_picks_in_progress(database):
    now = timezone.now()
    model = database.create(
        academy=1,
        city=1,
        country=1,
        event_type={"lang": "en", "description": "Workshop type"},
        event=[
            _event_kwargs("Live", now - timedelta(minutes=30), now + timedelta(hours=1)),
            _event_kwargs("Next", now + timedelta(days=1), now + timedelta(days=1, hours=2)),
        ],
    )
    for event in model.event:
        event.academy = model.academy
        event.save()

    canonical = canonical_group_event(GROUP, now=now)
    assert canonical.id == model.event[0].id


def test_public_all_returns_each_grouped_event(database):
    start1, end1 = _future_range(1)
    start2, end2 = _future_range(2)

    model = database.create(
        academy=1,
        city=1,
        country=1,
        event_type={"lang": "en", "description": "Workshop type"},
        event=[
            _event_kwargs("Day 1", start1, end1),
            _event_kwargs("Day 2", start2, end2),
        ],
    )

    response = Client().get(reverse("events:all"))

    assert response.status_code == 200
    group_rows = [event for event in response.json() if event.get("event_group") == GROUP]
    assert len(group_rows) == 2
    assert {event["id"] for event in group_rows} == {model.event[0].id, model.event[1].id}
