from datetime import datetime, timedelta
from datetime import timezone as dt_timezone

import capyc.pytest as capy
import pytest
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
        "recording_url": event.recording_url,
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
        "event_group": None,
        "variant": event.variant,
        "experiment_id": event.experiment_id,
        "product": event.product,
        "persona": event.persona,
        "product_persona": event.product_persona,
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


def utc(*args):
    return datetime(*args, tzinfo=dt_timezone.utc)


def create_events(database: capy.Database, fake: capy.Fake, ranges):
    return database.create(
        city=1,
        country=1,
        academy={
            "slug": fake.slug(),
            "name": fake.name(),
            "logo_url": "https://example.com/logo.jpg",
            "street_address": "Address",
        },
        event_type={
            "slug": fake.slug(),
            "name": fake.name(),
            "description": "description",
            "technologies": "python",
        },
        event=[
            {
                "title": f"My Event {n + 1}",
                "capacity": 100,
                "banner": "https://example.com/banner.jpg",
                "starting_at": starting_at,
                "ending_at": ending_at,
                "status": "ACTIVE",
                "event_type_id": 1,
            }
            for n, (starting_at, ending_at) in enumerate(ranges)
        ],
    )


FIXED_RANGES = [
    # 1: inside the range
    (utc(2030, 1, 11, 10), utc(2030, 1, 11, 12)),
    # 2: started before start, still running when the range begins
    (utc(2030, 1, 9, 10), utc(2030, 1, 10, 1)),
    # 3: entirely before the range
    (utc(2030, 1, 1, 10), utc(2030, 1, 2, 10)),
    # 4: entirely after the range
    (utc(2030, 1, 13, 10), utc(2030, 1, 13, 12)),
    # 5: starts at 23:00 on the end date
    (utc(2030, 1, 12, 23), utc(2030, 1, 13, 1)),
]


def get_ids(response):
    return [event["id"] for event in response.json()]


def test_filter_by_start_and_end_dates(client: capy.Client, database: capy.Database, fake: capy.Fake):
    url = reverse_lazy("events:all")
    create_events(database, fake, FIXED_RANGES)

    response = client.get(f"{url}?start=2030-01-10&end=2030-01-12")

    assert response.status_code == 200
    assert get_ids(response) == [2, 1, 5]


def test_filter_by_start_only(client: capy.Client, database: capy.Database, fake: capy.Fake):
    url = reverse_lazy("events:all")
    create_events(database, fake, FIXED_RANGES)

    response = client.get(f"{url}?start=2030-01-10")

    assert response.status_code == 200
    assert get_ids(response) == [2, 1, 5, 4]


def test_filter_by_end_only_includes_past_events(client: capy.Client, database: capy.Database, fake: capy.Fake):
    url = reverse_lazy("events:all")
    now = timezone.now()
    create_events(
        database,
        fake,
        [
            (now - timedelta(days=10), now - timedelta(days=10) + timedelta(hours=2)),
            (now + timedelta(days=10), now + timedelta(days=10) + timedelta(hours=2)),
        ],
    )

    end = (now - timedelta(days=1)).date().isoformat()
    response = client.get(f"{url}?end={end}")

    assert response.status_code == 200
    assert get_ids(response) == [1]


def test_filter_by_iso_datetimes(client: capy.Client, database: capy.Database, fake: capy.Fake):
    url = reverse_lazy("events:all")
    create_events(database, fake, FIXED_RANGES)

    response = client.get(f"{url}?start=2030-01-11T11:00:00Z&end=2030-01-11T11:30:00Z")

    assert response.status_code == 200
    assert get_ids(response) == [1]


def test_start_and_end_override_past(client: capy.Client, database: capy.Database, fake: capy.Fake):
    url = reverse_lazy("events:all")
    create_events(database, fake, FIXED_RANGES)

    response = client.get(f"{url}?past=true&start=2030-01-10&end=2030-01-12")

    assert response.status_code == 200
    assert get_ids(response) == [2, 1, 5]


@pytest.mark.parametrize(
    "querystring, slug",
    [
        ("start=not-a-date", "invalid-start-date"),
        ("end=2030-13-40", "invalid-end-date"),
        ("start=2030-01-12&end=2030-01-10", "start-after-end"),
        ("start=2030-01-11T12:00:00Z&end=2030-01-11T11:00:00Z", "start-after-end"),
    ],
)
def test_start_and_end_errors(client: capy.Client, database: capy.Database, querystring, slug):
    url = reverse_lazy("events:all")

    response = client.get(f"{url}?{querystring}")

    assert response.status_code == 400
    assert response.json() == {"detail": slug, "status_code": 400}


def test_filter_by_ago(client: capy.Client, database: capy.Database, fake: capy.Fake):
    url = reverse_lazy("events:all")
    now = timezone.now()
    create_events(
        database,
        fake,
        [
            # ended 2 hours ago
            (now - timedelta(hours=4), now - timedelta(hours=2)),
            # in progress
            (now - timedelta(hours=1), now + timedelta(hours=1)),
            # ended 2 days ago
            (now - timedelta(days=2, hours=2), now - timedelta(days=2)),
            # starts tomorrow
            (now + timedelta(days=1), now + timedelta(days=1, hours=2)),
        ],
    )

    response = client.get(f"{url}?ago=86400000")

    assert response.status_code == 200
    assert get_ids(response) == [1, 2]


def test_ago_overrides_past(client: capy.Client, database: capy.Database, fake: capy.Fake):
    url = reverse_lazy("events:all")
    now = timezone.now()
    create_events(
        database,
        fake,
        [
            (now - timedelta(hours=4), now - timedelta(hours=2)),
            (now - timedelta(days=2, hours=2), now - timedelta(days=2)),
        ],
    )

    response = client.get(f"{url}?past=true&ago=86400000")

    assert response.status_code == 200
    assert get_ids(response) == [1]


@pytest.mark.parametrize("ago", ["abc", "0", "-5", "1.5", str(10**20)])
def test_ago_invalid(client: capy.Client, database: capy.Database, ago):
    url = reverse_lazy("events:all")

    response = client.get(f"{url}?ago={ago}")

    assert response.status_code == 400
    assert response.json() == {"detail": "invalid-ago", "status_code": 400}


@pytest.mark.parametrize("extra", ["start=2030-01-10", "end=2030-01-12"])
def test_ago_with_start_or_end(client: capy.Client, database: capy.Database, extra):
    url = reverse_lazy("events:all")

    response = client.get(f"{url}?ago=86400000&{extra}")

    assert response.status_code == 400
    assert response.json() == {"detail": "ago-with-start-or-end", "status_code": 400}
