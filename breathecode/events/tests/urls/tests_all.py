from datetime import datetime, timedelta, timezone

import capyc.pytest as capy
from django.urls.base import reverse_lazy
from django.utils import timezone


def serialize_event(event):
    return {
        "id": event.id,
        "title": event.title,
        "starting_at": (
            event.starting_at.strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"
            if isinstance(event.starting_at, datetime)
            else None
        ),
        "ending_at": (
            event.ending_at.strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z" if isinstance(event.ending_at, datetime) else None
        ),
        "event_type": {
            "id": event.event_type.id,
            "slug": event.event_type.slug,
            "name": event.event_type.name,
            "technologies": event.event_type.technologies,
        },
        "slug": event.slug,
        "excerpt": event.excerpt,
        "lang": event.lang,
        "url": event.url,
        "banner": event.banner,
        "description": event.description,
        "capacity": event.capacity,
        "status": event.status,
        "host": event.host,
        "ended_at": (event.ended_at.strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z" if event.ended_at else None),
        "online_event": event.online_event,
        "is_public": event.is_public,
        "venue": (
            None
            if not event.venue
            else {
                "id": event.venue.id,
                "title": event.venue.title,
                "street_address": event.venue.street_address,
                "city": event.venue.city.name,
                "zip_code": event.venue.zip_code,
                "state": event.venue.state,
                "updated_at": event.venue.updated_at.isoformat(),
            }
        ),
        "academy": (
            None
            if not event.academy
            else {
                "id": event.academy.id,
                "slug": event.academy.slug,
                "name": event.academy.name,
                "city": {"name": event.academy.city.name} if event.academy.city else None,
            }
        ),
        "sync_with_eventbrite": event.sync_with_eventbrite,
        "eventbrite_sync_status": event.eventbrite_sync_status,
        "eventbrite_sync_description": event.eventbrite_sync_description,
        "tags": event.tags,
        "asset_slug": event.asset_slug,
        "host_user": (
            None
            if not event.host_user
            else {
                "id": event.host_user.id,
                "first_name": event.host_user.first_name,
                "last_name": event.host_user.last_name,
            }
        ),
        "author": (
            None
            if not event.author
            else {
                "id": event.author.id,
                "first_name": event.author.first_name,
                "last_name": event.author.last_name,
            }
        ),
        "asset": None,
    }


def test_filter_by_technologies(client: capy.Client, database: capy.Database, fake: capy.Fake):
    url = reverse_lazy("events:all")

    model = database.create(
        city=1,
        country=1,
        academy={
            "slug": fake.slug(),
            "name": fake.name(),
            "logo_url": "https://example.com/logo.jpg",
            "street_address": "Address",
        },
        event_type=[
            {
                "slug": fake.slug(),
                "name": fake.name(),
                "description": "description1",
                "technologies": "python, flask",
            },
            {
                "slug": fake.slug(),
                "name": fake.name(),
                "description": "description2",
                "technologies": "flask, pandas",
            },
        ],
        event=[
            {
                "title": "My First Event",
                "capacity": 100,
                "banner": "https://example.com/banner.jpg",
                "starting_at": timezone.now(),
                "ending_at": timezone.now() + timedelta(hours=2),
                "status": "ACTIVE",
                "event_type_id": n + 1,
            }
            for n in range(0, 2)
        ],
    )

    response = client.get(f"{url}?technologies=python")
    json = response.json()

    expected = [serialize_event(event) for event in model.event if "python" in event.event_type.technologies]

    assert response.status_code == 200
    assert expected == json


def test_filter_by_technologies_obtain_two(client: capy.Client, database: capy.Database, fake: capy.Fake):
    url = reverse_lazy("events:all")

    model = database.create(
        city=1,
        country=1,
        academy={
            "slug": fake.slug(),
            "name": fake.name(),
            "logo_url": "https://example.com/logo.jpg",
            "street_address": "Address",
        },
        event_type=[
            {
                "slug": fake.slug(),
                "name": fake.name(),
                "description": "description1",
                "technologies": "python, flask",
            },
            {
                "slug": fake.slug(),
                "name": fake.name(),
                "description": "description2",
                "technologies": "flask, pandas",
            },
            {
                "slug": fake.slug(),
                "name": fake.name(),
                "description": "description3",
                "technologies": "javascript, java",
            },
        ],
        event=[
            {
                "title": f"My Event {n + 1}",
                "capacity": 100,
                "banner": "https://example.com/banner.jpg",
                "starting_at": timezone.now(),
                "ending_at": timezone.now() + timedelta(hours=2),
                "status": "ACTIVE",
                "event_type_id": n + 1,
            }
            for n in range(3)
        ],
    )

    response = client.get(f"{url}?technologies=python,java")
    json = response.json()

    technologies_to_filter = {"python", "java"}
    expected = [
        serialize_event(event)
        for event in model.event
        if any(tech in event.event_type.technologies.split(", ") for tech in technologies_to_filter)
    ]

    assert response.status_code == 200
    assert expected == json


def test_all_academy_events_get_with_event_is_public_true_in_filter_is_public_true(
    client: capy.Client, database: capy.Database, fake: capy.Fake
):
    url = reverse_lazy("events:all")

    event_types = [
        {
            "slug": fake.slug(),
            "name": fake.name(),
            "description": "description1",
            "technologies": "python, flask",
        },
        {
            "slug": fake.slug(),
            "name": fake.name(),
            "description": "description2",
            "technologies": "javascript, react",
        },
    ]

    model = database.create(
        city=1,
        country=1,
        academy={
            "slug": fake.slug(),
            "name": fake.name(),
            "logo_url": "https://example.com/logo.jpg",
            "street_address": "Address",
        },
        event_type=event_types,
        event=[
            {
                "title": f"My Event {n + 1}",
                "capacity": 100,
                "banner": "https://example.com/banner.jpg",
                "starting_at": timezone.now(),
                "ending_at": timezone.now() + timedelta(hours=2),
                "status": "ACTIVE",
                "event_type_id": n + 1,
                "is_public": True,
            }
            for n in range(len(event_types))
        ],
    )

    response = client.get(f"{url}?is_public=true")
    json = response.json()

    expected = [serialize_event(event) for event in model.event if event.is_public]

    assert response.status_code == 200
    assert expected == json


def test_all_academy_events_get_with_event_is_public_false_in_filter_is_public_true(
    client: capy.Client, database: capy.Database, fake: capy.Fake
):
    url = reverse_lazy("events:all")

    event_types = [
        {
            "slug": fake.slug(),
            "name": fake.name(),
            "description": "description1",
            "technologies": "python, flask",
        },
        {
            "slug": fake.slug(),
            "name": fake.name(),
            "description": "description2",
            "technologies": "javascript, react",
        },
    ]

    model = database.create(
        city=1,
        country=1,
        academy={
            "slug": fake.slug(),
            "name": fake.name(),
            "logo_url": "https://example.com/logo.jpg",
            "street_address": "Address",
        },
        event_type=event_types,
        event=[
            {
                "title": f"My Event {n + 1}",
                "capacity": 100,
                "banner": "https://example.com/banner.jpg",
                "starting_at": timezone.now(),
                "ending_at": timezone.now() + timedelta(hours=2),
                "status": "ACTIVE",
                "event_type_id": n + 1,
                "is_public": False,
            }
            for n in range(len(event_types))
        ],
    )

    response = client.get(f"{url}?is_public=true")
    json = response.json()

    expected = [serialize_event(event) for event in model.event if event.is_public]

    assert response.status_code == 200
    assert expected == json


def test_all_academy_events_get_with_event_is_public_false_in_filter_is_public_false(
    client: capy.Client, database: capy.Database, fake: capy.Fake
):
    url = reverse_lazy("events:all")

    event_types = [
        {
            "slug": fake.slug(),
            "name": fake.name(),
            "description": "description1",
            "technologies": "python, flask",
        },
        {
            "slug": fake.slug(),
            "name": fake.name(),
            "description": "description2",
            "technologies": "javascript, react",
        },
    ]

    model = database.create(
        city=1,
        country=1,
        academy={
            "slug": fake.slug(),
            "name": fake.name(),
            "logo_url": "https://example.com/logo.jpg",
            "street_address": "Address",
        },
        event_type=event_types,
        event=[
            {
                "title": f"My Event {n + 1}",
                "capacity": 100,
                "banner": "https://example.com/banner.jpg",
                "starting_at": timezone.now(),
                "ending_at": timezone.now() + timedelta(hours=2),
                "status": "ACTIVE",
                "event_type_id": n + 1,
                "is_public": False,
            }
            for n in range(len(event_types))
        ],
    )

    response = client.get(f"{url}?is_public=false")
    json = response.json()

    expected = [serialize_event(event) for event in model.event if event.is_public == False]

    assert response.status_code == 200
    assert expected == json


def test_all_academy_events_get_with_event_is_public_true_in_filter_is_public_false(
    client: capy.Client, database: capy.Database, fake: capy.Fake
):
    url = reverse_lazy("events:all")

    event_types = [
        {
            "slug": fake.slug(),
            "name": fake.name(),
            "description": "description1",
            "technologies": "python, flask",
        },
        {
            "slug": fake.slug(),
            "name": fake.name(),
            "description": "description2",
            "technologies": "javascript, react",
        },
    ]

    model = database.create(
        city=1,
        country=1,
        academy={
            "slug": fake.slug(),
            "name": fake.name(),
            "logo_url": "https://example.com/logo.jpg",
            "street_address": "Address",
        },
        event_type=event_types,
        event=[
            {
                "title": f"My Event {n + 1}",
                "capacity": 100,
                "banner": "https://example.com/banner.jpg",
                "starting_at": timezone.now(),
                "ending_at": timezone.now() + timedelta(hours=2),
                "status": "ACTIVE",
                "event_type_id": n + 1,
                "is_public": True,
            }
            for n in range(len(event_types))
        ],
    )

    response = client.get(f"{url}?is_public=false")
    json = response.json()

    expected = [serialize_event(event) for event in model.event if event.is_public == False]

    assert response.status_code == 200
    assert expected == json
