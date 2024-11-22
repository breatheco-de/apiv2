from datetime import datetime, timedelta

import capyc.pytest as capy
from django.urls.base import reverse_lazy

from breathecode.admissions.models import Academy, City, Country
from breathecode.events.models import EventType


def test_filter_by_status(client: capy.Client, database: capy.Database):
    url = reverse_lazy("events:all")

    database.create(
        country={
            "code": "ES",
            "name": "Spain",
        }
    )
    country_instance = Country.objects.get(code="ES")

    database.create(
        city={
            "name": "Madrid",
            "country": country_instance,
        }
    )
    city_instance = City.objects.get(name="Madrid")

    academy = database.create(
        academy={
            "slug": "academy-1",
            "name": "My Academy",
            "logo_url": "https://example.com/logo.jpg",
            "street_address": "Address",
            "city": city_instance,
            "country": country_instance,
        }
    )
    academy_instance = Academy.objects.get(slug="academy-1")

    event_type1 = database.create(
        event_type={
            "slug": "EventType1",
            "name": "EventType 1",
            "description": "description1",
            "technologies": "python, flask",
            "academy": academy_instance,
        }
    )
    event_type1_instance = EventType.objects.get(slug="EventType1")
    event_type2 = database.create(
        event_type={
            "slug": "EventType2",
            "name": "EventType 2",
            "description": "description2",
            "technologies": "flask, pandas",
            "academy": academy_instance,
        }
    )
    event_type2_instance = EventType.objects.get(slug="EventType2")

    event1 = database.create(
        event={
            "title": "My First Event",
            "capacity": 100,
            "banner": "https://example.com/banner.jpg",
            "starting_at": datetime.now(),
            "ending_at": datetime.now() + timedelta(hours=2),
            "status": "ACTIVE",
            "event_type": event_type1_instance,
        }
    )
    event2 = database.create(
        event={
            "title": "My Second Event",
            "capacity": 100,
            "banner": "https://example.com/banner.jpg",
            "starting_at": datetime.now(),
            "ending_at": datetime.now() + timedelta(hours=2),
            "status": "ACTIVE",
            "event_type": event_type2_instance,
        }
    )

    response = client.get(f"{url}?technologies=python")
    json = response.json()

    assert response.status_code == 200
    assert len(json) == 1
    assert json[0]["event_type"]["technologies"] == "python, flask"
