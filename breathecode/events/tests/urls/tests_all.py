from datetime import datetime, timedelta

import capyc.pytest as capy
from django.urls.base import reverse_lazy


def serialize_event(event):
    return {
        "id": event.id,
        "title": event.title,
        "starting_at": event.starting_at.isoformat() if isinstance(event.starting_at, datetime) else event.starting_at,
        "ending_at": event.ending_at.isoformat() if isinstance(event.ending_at, datetime) else event.ending_at,
        "event_type": {
            "id": event.event_type.id,
            "slug": event.event_type.slug,
            "name": event.event_type.name,
            "technologies": event.event_type.technologies,
        },
        "slug": event.slug,
        "excerpt": event.excerpt or None,
        "lang": event.lang or None,
        "url": event.url or None,
        "banner": event.banner,
        "description": event.description or None,
        "capacity": event.capacity,
        "status": event.status,
        "host": event.host or None,
        "ended_at": event.ended_at.isoformat() if event.ended_at else None,
        "online_event": event.online_event,
        "venue": (
            {
                "id": event.venue.id,
                "title": event.venue.title,
                "street_address": event.venue.street_address,
                "city": event.venue.city.name,
                "zip_code": event.venue.zip_code,
                "state": event.venue.state,
                "updated_at": event.venue.updated_at.isoformat(),
            }
            if event.venue
            else None
        ),
        "academy": (
            {
                "id": event.academy.id,
                "slug": event.academy.slug,
                "name": event.academy.name,
                "city": {"name": event.academy.city.name} if event.academy.city else None,
            }
            if event.academy
            else None
        ),
        "sync_with_eventbrite": event.sync_with_eventbrite,
        "eventbrite_sync_status": event.eventbrite_sync_status or None,
        "eventbrite_sync_description": event.eventbrite_sync_description or None,
        "tags": event.tags or None,
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
    }


def test_filter_by_status(client: capy.Client, database: capy.Database, fake: capy.Fake):
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
                "starting_at": datetime.now(),
                "ending_at": datetime.now() + timedelta(hours=2),
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
    assert len(json) == 1
    assert json[0]["event_type"]["technologies"] == "python, flask"
