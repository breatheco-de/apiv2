"""
Test /academy/cohort
"""

import urllib
from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.urls.base import reverse_lazy
from django.utils import timezone
from rest_framework import status

from ..mixins.new_events_tests_case import EventTestCase


class AcademyCohortTestSuite(EventTestCase):
    """Test /academy/cohort"""

    def test_ical_events__without_academy(self):
        """Test /academy/cohort without auth"""
        url = reverse_lazy("events:ical_events")
        args = {"academy": "1"}
        response = self.client.get(url + "?" + urllib.parse.urlencode(args))
        json = response.json()

        expected = {"detail": "Some academy not exist", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_ical_events__without_events(self):
        """Test /academy/cohort without auth"""
        device_id_kwargs = {"name": "server"}
        model = self.generate_models(academy=True, device_id=True, device_id_kwargs=device_id_kwargs)

        url = reverse_lazy("events:ical_events")
        args = {"academy": "1"}
        response = self.client.get(url + "?" + urllib.parse.urlencode(args))

        key = model.device_id.key
        expected = "\r\n".join(
            [
                "BEGIN:VCALENDAR",
                "VERSION:2.0",
                f"PRODID:-//4Geeks//Academy Events (1) {key}//EN",
                "METHOD:PUBLISH",
                "REFRESH-INTERVAL;VALUE=DURATION:PT15M",
                "URL:http://localhost:8000/v1/events/ical/events?academy=1",
                "X-WR-CALDESC:",
                f"X-WR-CALNAME:Academy - Events",
                "END:VCALENDAR",
                "",
            ]
        )

        self.assertEqual(response.content.decode("utf-8"), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_ical_events__dont_get_status_draft(self):
        """Test /academy/cohort without auth"""
        device_id_kwargs = {"name": "server"}
        model = self.generate_models(academy=True, event=True, device_id=True, device_id_kwargs=device_id_kwargs)

        url = reverse_lazy("events:ical_events")
        args = {"academy": "1"}
        response = self.client.get(url + "?" + urllib.parse.urlencode(args))

        academy = model["academy"]
        key = model.device_id.key
        expected = "\r\n".join(
            [
                "BEGIN:VCALENDAR",
                "VERSION:2.0",
                f"PRODID:-//4Geeks//Academy Events (1) {key}//EN",
                "METHOD:PUBLISH",
                "REFRESH-INTERVAL;VALUE=DURATION:PT15M",
                "URL:http://localhost:8000/v1/events/ical/events?academy=1",
                "X-WR-CALDESC:",
                f"X-WR-CALNAME:Academy - Events",
                "END:VCALENDAR",
                "",
            ]
        )

        self.assertEqual(response.content.decode("utf-8"), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_ical_events__dont_get_status_deleted(self):
        """Test /academy/cohort without auth"""
        event_kwargs = {"status": "DELETED"}
        device_id_kwargs = {"name": "server"}
        model = self.generate_models(
            academy=True, event=True, device_id=True, event_kwargs=event_kwargs, device_id_kwargs=device_id_kwargs
        )

        url = reverse_lazy("events:ical_events")
        args = {"academy": "1"}
        response = self.client.get(url + "?" + urllib.parse.urlencode(args))

        academy = model["academy"]
        key = model.device_id.key
        expected = "\r\n".join(
            [
                "BEGIN:VCALENDAR",
                "VERSION:2.0",
                f"PRODID:-//4Geeks//Academy Events (1) {key}//EN",
                "METHOD:PUBLISH",
                "REFRESH-INTERVAL;VALUE=DURATION:PT15M",
                "URL:http://localhost:8000/v1/events/ical/events?academy=1",
                "X-WR-CALDESC:",
                f"X-WR-CALNAME:Academy - Events",
                "END:VCALENDAR",
                "",
            ]
        )

        self.assertEqual(response.content.decode("utf-8"), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_ical_events__with_one(self):
        """Test /academy/cohort without auth"""
        event_kwargs = {"status": "ACTIVE"}
        device_id_kwargs = {"name": "server"}
        model = self.generate_models(
            academy=True,
            user=True,
            event=True,
            device_id=True,
            event_kwargs=event_kwargs,
            device_id_kwargs=device_id_kwargs,
        )

        url = reverse_lazy("events:ical_events")
        args = {"academy": "1"}
        response = self.client.get(url + "?" + urllib.parse.urlencode(args))

        event = model["event"]
        user = model["user"]
        academy = model["academy"]
        key = model.device_id.key
        expected = "\r\n".join(
            [
                "BEGIN:VCALENDAR",
                "VERSION:2.0",
                f"PRODID:-//4Geeks//Academy Events (1) {key}//EN",
                "METHOD:PUBLISH",
                "REFRESH-INTERVAL;VALUE=DURATION:PT15M",
                "URL:http://localhost:8000/v1/events/ical/events?academy=1",
                "X-WR-CALDESC:",
                f"X-WR-CALNAME:Academy - Events",
                # event
                "BEGIN:VEVENT",
                f"DTSTART:{self.datetime_to_ical(event.starting_at)}",
                f"DTEND:{self.datetime_to_ical(event.ending_at)}",
                f"DTSTAMP:{self.datetime_to_ical(event.created_at)}",
                f"UID:breathecode_event_{event.id}_{key}",
                self.line_limit(f"DESCRIPTION:Url: {event.url}\\nAcademy: " f"{event.academy.name}\\n"),
                self.line_limit(f'ORGANIZER;CN="{user.first_name} {user.last_name}";ROLE=OWNER:MAILTO:{user.email}'),
                "END:VEVENT",
                "END:VCALENDAR",
                "",
            ]
        )

        self.assertEqual(response.content.decode("utf-8"), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_ical_events__with_one_and_online_event(self):
        """Test /academy/cohort without auth"""
        event_kwargs = {"status": "ACTIVE", "online_event": True}
        device_id_kwargs = {"name": "server"}
        model = self.generate_models(
            academy=True,
            user=True,
            event=True,
            device_id=True,
            event_kwargs=event_kwargs,
            device_id_kwargs=device_id_kwargs,
        )

        url = reverse_lazy("events:ical_events")
        args = {"academy": "1"}
        response = self.client.get(url + "?" + urllib.parse.urlencode(args))

        event = model["event"]
        user = model["user"]
        academy = model["academy"]
        key = model.device_id.key
        expected = "\r\n".join(
            [
                "BEGIN:VCALENDAR",
                "VERSION:2.0",
                f"PRODID:-//4Geeks//Academy Events (1) {key}//EN",
                "METHOD:PUBLISH",
                "REFRESH-INTERVAL;VALUE=DURATION:PT15M",
                "URL:http://localhost:8000/v1/events/ical/events?academy=1",
                "X-WR-CALDESC:",
                f"X-WR-CALNAME:Academy - Events",
                # event
                "BEGIN:VEVENT",
                f"DTSTART:{self.datetime_to_ical(event.starting_at)}",
                f"DTEND:{self.datetime_to_ical(event.ending_at)}",
                f"DTSTAMP:{self.datetime_to_ical(event.created_at)}",
                f"UID:breathecode_event_{event.id}_{key}",
                self.line_limit(
                    f"DESCRIPTION:Url: {event.url}\\nAcademy: " f"{event.academy.name}\\nLocation: online\\n"
                ),
                self.line_limit(f'ORGANIZER;CN="{user.first_name} {user.last_name}";ROLE=OWNER:MAILTO:{user.email}'),
                "END:VEVENT",
                "END:VCALENDAR",
                "",
            ]
        )

        self.assertEqual(response.content.decode("utf-8"), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_ical_events__with_one_and_venue(self):
        """Test /academy/cohort without auth"""
        event_kwargs = {"status": "ACTIVE"}
        device_id_kwargs = {"name": "server"}
        venue_kwargs = {
            "title": "Title",
            "street_address": "Street 2 #10-51",
            "city": "Gaira",
            "state": "Magdalena",
            "country": "Colombia",
        }

        model = self.generate_models(
            academy=True,
            user=True,
            event=True,
            device_id=True,
            venue=True,
            event_kwargs=event_kwargs,
            venue_kwargs=venue_kwargs,
            device_id_kwargs=device_id_kwargs,
        )
        url = reverse_lazy("events:ical_events")
        args = {"academy": "1"}
        response = self.client.get(url + "?" + urllib.parse.urlencode(args))

        event = model["event"]
        user = model["user"]
        academy = model["academy"]
        key = model.device_id.key
        expected = "\r\n".join(
            [
                "BEGIN:VCALENDAR",
                "VERSION:2.0",
                f"PRODID:-//4Geeks//Academy Events (1) {key}//EN",
                "METHOD:PUBLISH",
                "REFRESH-INTERVAL;VALUE=DURATION:PT15M",
                "URL:http://localhost:8000/v1/events/ical/events?academy=1",
                "X-WR-CALDESC:",
                f"X-WR-CALNAME:Academy - Events",
                # event
                "BEGIN:VEVENT",
                f"DTSTART:{self.datetime_to_ical(event.starting_at)}",
                f"DTEND:{self.datetime_to_ical(event.ending_at)}",
                f"DTSTAMP:{self.datetime_to_ical(event.created_at)}",
                f"UID:breathecode_event_{event.id}_{key}",
                self.line_limit(
                    f"DESCRIPTION:Url: {event.url}\\nAcademy: "
                    f"{event.academy.name}\\nVenue: {event.venue.title}\\n"
                    ""
                ),
                "LOCATION:Street 2 #10-51\\, Gaira\\, Magdalena\\, Colombia",
                self.line_limit(f'ORGANIZER;CN="{user.first_name} {user.last_name}";ROLE=OWNER:MAILTO:{user.email}'),
                "END:VEVENT",
                "END:VCALENDAR",
                "",
            ]
        )

        self.assertEqual(response.content.decode("utf-8"), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_ical_events__with_one_and_venue__upcoming_true__return_zero_events(self):
        """Test /academy/cohort without auth"""
        device_id_kwargs = {"name": "server"}
        event_kwargs = {
            "status": "ACTIVE",
            "starting_at": timezone.now() - timedelta(days=1),
        }
        venue_kwargs = {
            "street_address": "Street 2 #10-51",
            "city": "Gaira",
            "state": "Magdalena",
            "country": "Colombia",
        }

        model = self.generate_models(
            academy=True,
            user=True,
            event=True,
            device_id=True,
            venue=True,
            event_kwargs=event_kwargs,
            venue_kwargs=venue_kwargs,
            device_id_kwargs=device_id_kwargs,
        )
        url = reverse_lazy("events:ical_events")
        args = {"academy": "1", "upcoming": "true"}
        response = self.client.get(url + "?" + urllib.parse.urlencode(args))

        key = model.device_id.key
        expected = "\r\n".join(
            [
                "BEGIN:VCALENDAR",
                "VERSION:2.0",
                f"PRODID:-//4Geeks//Academy Events (1) {key}//EN",
                "METHOD:PUBLISH",
                "REFRESH-INTERVAL;VALUE=DURATION:PT15M",
                "URL:http://localhost:8000/v1/events/ical/events?academy=1",
                "X-WR-CALDESC:",
                f"X-WR-CALNAME:Academy - Events",
                "END:VCALENDAR",
                "",
            ]
        )

        self.assertEqual(response.content.decode("utf-8"), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_ical_events__with_one_and_venue__upcoming_true(self):
        """Test /academy/cohort without auth"""
        device_id_kwargs = {"name": "server"}
        event_kwargs = {
            "status": "ACTIVE",
            "starting_at": timezone.now() + timedelta(days=1),
        }
        venue_kwargs = {
            "title": "Title",
            "street_address": "Street 2 #10-51",
            "city": "Gaira",
            "state": "Magdalena",
            "country": "Colombia",
        }

        model = self.generate_models(
            academy=True,
            user=True,
            event=True,
            device_id=True,
            venue=True,
            event_kwargs=event_kwargs,
            venue_kwargs=venue_kwargs,
            device_id_kwargs=device_id_kwargs,
        )

        url = reverse_lazy("events:ical_events")
        args = {"academy": "1", "upcoming": "true"}
        response = self.client.get(url + "?" + urllib.parse.urlencode(args))

        event = model["event"]
        user = model["user"]
        key = model.device_id.key
        expected = "\r\n".join(
            [
                "BEGIN:VCALENDAR",
                "VERSION:2.0",
                f"PRODID:-//4Geeks//Academy Events (1) {key}//EN",
                "METHOD:PUBLISH",
                "REFRESH-INTERVAL;VALUE=DURATION:PT15M",
                "URL:http://localhost:8000/v1/events/ical/events?academy=1",
                "X-WR-CALDESC:",
                f"X-WR-CALNAME:Academy - Events",
                # event
                "BEGIN:VEVENT",
                f"DTSTART:{self.datetime_to_ical(event.starting_at)}",
                f"DTEND:{self.datetime_to_ical(event.ending_at)}",
                f"DTSTAMP:{self.datetime_to_ical(event.created_at)}",
                f"UID:breathecode_event_{event.id}_{key}",
                self.line_limit(
                    f"DESCRIPTION:Url: {event.url}\\nAcademy: "
                    f"{event.academy.name}\\nVenue: {event.venue.title}\\n"
                    ""
                ),
                "LOCATION:Street 2 #10-51\\, Gaira\\, Magdalena\\, Colombia",
                self.line_limit(f'ORGANIZER;CN="{user.first_name} {user.last_name}";ROLE=OWNER:MAILTO:{user.email}'),
                "END:VEVENT",
                "END:VCALENDAR",
                "",
            ]
        )

        self.assertEqual(response.content.decode("utf-8"), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_ical_events__with_two(self):
        """Test /academy/cohort without auth"""
        event_kwargs = {"status": "ACTIVE"}
        device_id_kwargs = {"name": "server"}
        base = self.generate_models(device_id=True, academy=True, device_id_kwargs=device_id_kwargs)

        models = [
            self.generate_models(user=True, event=True, event_kwargs=event_kwargs, models=base),
            self.generate_models(user=True, event=True, event_kwargs=event_kwargs, models=base),
        ]

        url = reverse_lazy("events:ical_events")
        args = {"academy": "1"}
        response = self.client.get(url + "?" + urllib.parse.urlencode(args))

        event1 = models[0]["event"]
        event2 = models[1]["event"]
        user1 = models[0]["user"]
        user2 = models[1]["user"]
        academy = models[0]["academy"]
        key = base.device_id.key
        expected = "\r\n".join(
            [
                "BEGIN:VCALENDAR",
                "VERSION:2.0",
                f"PRODID:-//4Geeks//Academy Events (1) {key}//EN",
                "METHOD:PUBLISH",
                "REFRESH-INTERVAL;VALUE=DURATION:PT15M",
                "URL:http://localhost:8000/v1/events/ical/events?academy=1",
                "X-WR-CALDESC:",
                f"X-WR-CALNAME:Academy - Events",
                # event
                "BEGIN:VEVENT",
                f"DTSTART:{self.datetime_to_ical(event1.starting_at)}",
                f"DTEND:{self.datetime_to_ical(event1.ending_at)}",
                f"DTSTAMP:{self.datetime_to_ical(event1.created_at)}",
                f"UID:breathecode_event_{event1.id}_{key}",
                self.line_limit(f"DESCRIPTION:Url: {event1.url}\\nAcademy: " f"{event1.academy.name}\\n"),
                self.line_limit(f'ORGANIZER;CN="{user1.first_name} {user1.last_name}";ROLE=OWNER:MAILTO:{user1.email}'),
                "END:VEVENT",
                # event
                "BEGIN:VEVENT",
                f"DTSTART:{self.datetime_to_ical(event2.starting_at)}",
                f"DTEND:{self.datetime_to_ical(event2.ending_at)}",
                f"DTSTAMP:{self.datetime_to_ical(event2.created_at)}",
                f"UID:breathecode_event_{event2.id}_{key}",
                self.line_limit(f"DESCRIPTION:Url: {event2.url}\\nAcademy: " f"{event2.academy.name}\\n"),
                self.line_limit(f'ORGANIZER;CN="{user2.first_name} {user2.last_name}";ROLE=OWNER:MAILTO:{user2.email}'),
                "END:VEVENT",
                "END:VCALENDAR",
                "",
            ]
        )

        self.assertEqual(response.content.decode("utf-8"), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_ical_events__with_two_and_venue(self):
        """Test /academy/cohort without auth"""
        event_kwargs = {"status": "ACTIVE"}
        venue_kwargs = {
            "title": "Title",
            "street_address": "Street 2 #10-51",
            "city": "Gaira",
            "state": "Magdalena",
            "country": "Colombia",
        }
        device_id_kwargs = {"name": "server"}
        base = self.generate_models(device_id=True, academy=True, device_id_kwargs=device_id_kwargs)

        models = [
            self.generate_models(
                user=True, event=True, venue=True, event_kwargs=event_kwargs, venue_kwargs=venue_kwargs, models=base
            ),
            self.generate_models(
                user=True, event=True, venue=True, event_kwargs=event_kwargs, venue_kwargs=venue_kwargs, models=base
            ),
        ]

        url = reverse_lazy("events:ical_events")
        args = {"academy": "1"}
        response = self.client.get(url + "?" + urllib.parse.urlencode(args))

        event1 = models[0]["event"]
        event2 = models[1]["event"]
        user1 = models[0]["user"]
        user2 = models[1]["user"]
        academy = models[0]["academy"]
        key = base.device_id.key
        expected = "\r\n".join(
            [
                "BEGIN:VCALENDAR",
                "VERSION:2.0",
                f"PRODID:-//4Geeks//Academy Events (1) {key}//EN",
                "METHOD:PUBLISH",
                "REFRESH-INTERVAL;VALUE=DURATION:PT15M",
                "URL:http://localhost:8000/v1/events/ical/events?academy=1",
                "X-WR-CALDESC:",
                f"X-WR-CALNAME:Academy - Events",
                # event
                "BEGIN:VEVENT",
                f"DTSTART:{self.datetime_to_ical(event1.starting_at)}",
                f"DTEND:{self.datetime_to_ical(event1.ending_at)}",
                f"DTSTAMP:{self.datetime_to_ical(event1.created_at)}",
                f"UID:breathecode_event_{event1.id}_{key}",
                self.line_limit(
                    f"DESCRIPTION:Url: {event1.url}\\nAcademy: "
                    f"{event1.academy.name}\\nVenue: {event1.venue.title}\\n"
                    ""
                ),
                "LOCATION:Street 2 #10-51\\, Gaira\\, Magdalena\\, Colombia",
                self.line_limit(f'ORGANIZER;CN="{user1.first_name} {user1.last_name}";ROLE=OWNER:MAILTO:{user1.email}'),
                "END:VEVENT",
                # event
                "BEGIN:VEVENT",
                f"DTSTART:{self.datetime_to_ical(event2.starting_at)}",
                f"DTEND:{self.datetime_to_ical(event2.ending_at)}",
                f"DTSTAMP:{self.datetime_to_ical(event2.created_at)}",
                f"UID:breathecode_event_{event2.id}_{key}",
                self.line_limit(
                    f"DESCRIPTION:Url: {event2.url}\\nAcademy: "
                    f"{event2.academy.name}\\nVenue: {event2.venue.title}\\n"
                    ""
                ),
                "LOCATION:Street 2 #10-51\\, Gaira\\, Magdalena\\, Colombia",
                self.line_limit(f'ORGANIZER;CN="{user2.first_name} {user2.last_name}";ROLE=OWNER:MAILTO:{user2.email}'),
                "END:VEVENT",
                "END:VCALENDAR",
                "",
            ]
        )

        self.assertEqual(response.content.decode("utf-8"), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_ical_events__with_two_and_venue__with_two_academies_id(self):
        """Test /academy/cohort without auth"""
        event_kwargs = {"status": "ACTIVE"}
        venue_kwargs = {
            "title": "Title",
            "street_address": "Street 2 #10-51",
            "city": "Gaira",
            "state": "Magdalena",
            "country": "Colombia",
        }
        device_id_kwargs = {"name": "server"}
        base = self.generate_models(device_id=True, device_id_kwargs=device_id_kwargs)
        base1 = self.generate_models(academy=True, models=base)

        models = [
            self.generate_models(
                user=True, event=True, venue=True, event_kwargs=event_kwargs, venue_kwargs=venue_kwargs, models=base1
            ),
            self.generate_models(
                user=True, event=True, venue=True, event_kwargs=event_kwargs, venue_kwargs=venue_kwargs, models=base1
            ),
        ]

        base2 = self.generate_models(academy=True, models=base)

        models = models + [
            self.generate_models(
                user=True, event=True, venue=True, event_kwargs=event_kwargs, venue_kwargs=venue_kwargs, models=base2
            ),
            self.generate_models(
                user=True, event=True, venue=True, event_kwargs=event_kwargs, venue_kwargs=venue_kwargs, models=base2
            ),
        ]

        url = reverse_lazy("events:ical_events")
        args = {"academy": "1,2"}
        url = url + "?" + urllib.parse.urlencode(args)
        response = self.client.get(url)

        event1 = models[0]["event"]
        event2 = models[1]["event"]
        event3 = models[2]["event"]
        event4 = models[3]["event"]
        user1 = models[0]["user"]
        user2 = models[1]["user"]
        user3 = models[2]["user"]
        user4 = models[3]["user"]
        key = base.device_id.key
        url = url.replace("%2C", ",")
        expected = "\r\n".join(
            [
                "BEGIN:VCALENDAR",
                "VERSION:2.0",
                f"PRODID:-//4Geeks//Academy Events (1\\,2) {key}//EN",
                "METHOD:PUBLISH",
                "REFRESH-INTERVAL;VALUE=DURATION:PT15M",
                self.line_limit(f"URL:http://localhost:8000{url}"),
                "X-WR-CALDESC:",
                f"X-WR-CALNAME:Academy - Events",
                # event
                "BEGIN:VEVENT",
                f"DTSTART:{self.datetime_to_ical(event1.starting_at)}",
                f"DTEND:{self.datetime_to_ical(event1.ending_at)}",
                f"DTSTAMP:{self.datetime_to_ical(event1.created_at)}",
                f"UID:breathecode_event_{event1.id}_{key}",
                self.line_limit(
                    f"DESCRIPTION:Url: {event1.url}\\nAcademy: "
                    f"{event1.academy.name}\\nVenue: {event1.venue.title}\\n"
                    ""
                ),
                "LOCATION:Street 2 #10-51\\, Gaira\\, Magdalena\\, Colombia",
                self.line_limit(f'ORGANIZER;CN="{user1.first_name} {user1.last_name}";ROLE=OWNER:MAILTO:{user1.email}'),
                "END:VEVENT",
                # event
                "BEGIN:VEVENT",
                f"DTSTART:{self.datetime_to_ical(event2.starting_at)}",
                f"DTEND:{self.datetime_to_ical(event2.ending_at)}",
                f"DTSTAMP:{self.datetime_to_ical(event2.created_at)}",
                f"UID:breathecode_event_{event2.id}_{key}",
                self.line_limit(
                    f"DESCRIPTION:Url: {event2.url}\\nAcademy: "
                    f"{event2.academy.name}\\nVenue: {event2.venue.title}\\n"
                    ""
                ),
                "LOCATION:Street 2 #10-51\\, Gaira\\, Magdalena\\, Colombia",
                self.line_limit(f'ORGANIZER;CN="{user2.first_name} {user2.last_name}";ROLE=OWNER:MAILTO:{user2.email}'),
                "END:VEVENT",
                # event
                "BEGIN:VEVENT",
                f"DTSTART:{self.datetime_to_ical(event3.starting_at)}",
                f"DTEND:{self.datetime_to_ical(event3.ending_at)}",
                f"DTSTAMP:{self.datetime_to_ical(event3.created_at)}",
                f"UID:breathecode_event_{event3.id}_{key}",
                self.line_limit(
                    f"DESCRIPTION:Url: {event3.url}\\nAcademy: "
                    f"{event3.academy.name}\\nVenue: {event3.venue.title}\\n"
                    ""
                ),
                "LOCATION:Street 2 #10-51\\, Gaira\\, Magdalena\\, Colombia",
                self.line_limit(f'ORGANIZER;CN="{user3.first_name} {user3.last_name}";ROLE=OWNER:MAILTO:{user3.email}'),
                "END:VEVENT",
                # event
                "BEGIN:VEVENT",
                f"DTSTART:{self.datetime_to_ical(event4.starting_at)}",
                f"DTEND:{self.datetime_to_ical(event4.ending_at)}",
                f"DTSTAMP:{self.datetime_to_ical(event4.created_at)}",
                f"UID:breathecode_event_{event4.id}_{key}",
                self.line_limit(
                    f"DESCRIPTION:Url: {event4.url}\\nAcademy: "
                    f"{event4.academy.name}\\nVenue: {event4.venue.title}\\n"
                    ""
                ),
                "LOCATION:Street 2 #10-51\\, Gaira\\, Magdalena\\, Colombia",
                self.line_limit(f'ORGANIZER;CN="{user4.first_name} {user4.last_name}";ROLE=OWNER:MAILTO:{user4.email}'),
                "END:VEVENT",
                "END:VCALENDAR",
                "",
            ]
        )

        self.assertEqual(response.content.decode("utf-8"), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_ical_events__with_two_and_venue__with_two_academies_slug(self):
        """Test /academy/cohort without auth"""
        event_kwargs = {"status": "ACTIVE"}
        venue_kwargs = {
            "title": "Title",
            "street_address": "Street 2 #10-51",
            "city": "Gaira",
            "state": "Magdalena",
            "country": "Colombia",
        }
        device_id_kwargs = {"name": "server"}
        base = self.generate_models(device_id=True, device_id_kwargs=device_id_kwargs)
        base1 = self.generate_models(academy=True, models=base)

        models = [
            self.generate_models(
                user=True, event=True, venue=True, event_kwargs=event_kwargs, venue_kwargs=venue_kwargs, models=base1
            ),
            self.generate_models(
                user=True, event=True, venue=True, event_kwargs=event_kwargs, venue_kwargs=venue_kwargs, models=base1
            ),
        ]

        base2 = self.generate_models(academy=True, models=base)

        models = models + [
            self.generate_models(
                user=True, event=True, venue=True, event_kwargs=event_kwargs, venue_kwargs=venue_kwargs, models=base2
            ),
            self.generate_models(
                user=True, event=True, venue=True, event_kwargs=event_kwargs, venue_kwargs=venue_kwargs, models=base2
            ),
        ]

        url = reverse_lazy("events:ical_events")
        args = {"academy_slug": ",".join(list(dict.fromkeys([x.academy.slug for x in models])))}
        url = url + "?" + urllib.parse.urlencode(args)
        response = self.client.get(url + "?" + urllib.parse.urlencode(args))

        event1 = models[0]["event"]
        event2 = models[1]["event"]
        event3 = models[2]["event"]
        event4 = models[3]["event"]
        user1 = models[0]["user"]
        user2 = models[1]["user"]
        user3 = models[2]["user"]
        user4 = models[3]["user"]
        key = base.device_id.key
        url = url.replace("%2C", ",")
        expected = "\r\n".join(
            [
                "BEGIN:VCALENDAR",
                "VERSION:2.0",
                f"PRODID:-//4Geeks//Academy Events (1\\,2) {key}//EN",
                "METHOD:PUBLISH",
                "REFRESH-INTERVAL;VALUE=DURATION:PT15M",
                self.line_limit(f"URL:http://localhost:8000{url}"),
                "X-WR-CALDESC:",
                f"X-WR-CALNAME:Academy - Events",
                # event
                "BEGIN:VEVENT",
                f"DTSTART:{self.datetime_to_ical(event1.starting_at)}",
                f"DTEND:{self.datetime_to_ical(event1.ending_at)}",
                f"DTSTAMP:{self.datetime_to_ical(event1.created_at)}",
                f"UID:breathecode_event_{event1.id}_{key}",
                self.line_limit(
                    f"DESCRIPTION:Url: {event1.url}\\nAcademy: "
                    f"{event1.academy.name}\\nVenue: {event1.venue.title}\\n"
                    ""
                ),
                "LOCATION:Street 2 #10-51\\, Gaira\\, Magdalena\\, Colombia",
                self.line_limit(f'ORGANIZER;CN="{user1.first_name} {user1.last_name}";ROLE=OWNER:MAILTO:{user1.email}'),
                "END:VEVENT",
                # event
                "BEGIN:VEVENT",
                f"DTSTART:{self.datetime_to_ical(event2.starting_at)}",
                f"DTEND:{self.datetime_to_ical(event2.ending_at)}",
                f"DTSTAMP:{self.datetime_to_ical(event2.created_at)}",
                f"UID:breathecode_event_{event2.id}_{key}",
                self.line_limit(
                    f"DESCRIPTION:Url: {event2.url}\\nAcademy: "
                    f"{event2.academy.name}\\nVenue: {event2.venue.title}\\n"
                    ""
                ),
                "LOCATION:Street 2 #10-51\\, Gaira\\, Magdalena\\, Colombia",
                self.line_limit(f'ORGANIZER;CN="{user2.first_name} {user2.last_name}";ROLE=OWNER:MAILTO:{user2.email}'),
                "END:VEVENT",
                # event
                "BEGIN:VEVENT",
                f"DTSTART:{self.datetime_to_ical(event3.starting_at)}",
                f"DTEND:{self.datetime_to_ical(event3.ending_at)}",
                f"DTSTAMP:{self.datetime_to_ical(event3.created_at)}",
                f"UID:breathecode_event_{event3.id}_{key}",
                self.line_limit(
                    f"DESCRIPTION:Url: {event3.url}\\nAcademy: "
                    f"{event3.academy.name}\\nVenue: {event3.venue.title}\\n"
                    ""
                ),
                "LOCATION:Street 2 #10-51\\, Gaira\\, Magdalena\\, Colombia",
                self.line_limit(f'ORGANIZER;CN="{user3.first_name} {user3.last_name}";ROLE=OWNER:MAILTO:{user3.email}'),
                "END:VEVENT",
                # event
                "BEGIN:VEVENT",
                f"DTSTART:{self.datetime_to_ical(event4.starting_at)}",
                f"DTEND:{self.datetime_to_ical(event4.ending_at)}",
                f"DTSTAMP:{self.datetime_to_ical(event4.created_at)}",
                f"UID:breathecode_event_{event4.id}_{key}",
                self.line_limit(
                    f"DESCRIPTION:Url: {event4.url}\\nAcademy: "
                    f"{event4.academy.name}\\nVenue: {event4.venue.title}\\n"
                    ""
                ),
                "LOCATION:Street 2 #10-51\\, Gaira\\, Magdalena\\, Colombia",
                self.line_limit(f'ORGANIZER;CN="{user4.first_name} {user4.last_name}";ROLE=OWNER:MAILTO:{user4.email}'),
                "END:VEVENT",
                "END:VCALENDAR",
                "",
            ]
        )

        self.assertEqual(response.content.decode("utf-8"), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # # this test is comment because is util to check and generate one example
    # # ical file
    #
    # def test_generate_ical(self):
    #     """Test /academy/cohort without auth"""
    #     from faker import Faker
    #     from datetime import datetime, timedelta

    #     fake = Faker()
    #     event_kwargs = {
    #         'status': 'ACTIVE',
    #         'title': fake.name(),
    #         'description': fake.text(),
    #         'starting_at': datetime.now() + timedelta(days=1, hours=12),
    #         'ending_at': datetime.now() + timedelta(days=1, hours=15),
    #     }

    #     base = self.generate_models(authenticate=True, profile_academy=True,
    #             capability='read_event', role='potato', academy=True)

    #     models = [
    #         self.generate_models(user=True, event=True, event_kwargs=event_kwargs,
    #             models=base),
    #         self.generate_models(user=True, event=True, event_kwargs=event_kwargs,
    #             models=base),
    #     ]

    #     url = reverse_lazy('events:ical_events', args={'academy': "1"})
    #     response = self.client.get(url)

    #     import os

    #     calendar_path = os.path.join('C:\\', 'Users', 'admin', 'desktop', 'calendar.ics')
    #     with open(calendar_path, 'w') as file:
    #         file.write(response.content.decode('utf-8').replace('\r', ''))

    #     assert False
