from datetime import timedelta
from django.utils import timezone
from ..mixins import MonitoringTestCase
from breathecode.monitoring.actions import run_script
from breathecode.admissions.models import Cohort, Academy


class AcademyCohortTestSuite(MonitoringTestCase):
    """
    🔽🔽🔽 With zero Event
    """

    def test_event_marked_as_draft__zero_events(self):
        """
        Descriptions of models are being generated:

          Academy(id=1):
            city: City(id=1)
            country: Country(code="XLx")

          Application(id=1):
            academy: Academy(id=1)

          MonitorScript(id=1):
            application: Application(id=1)
        """

        monitor_script = {"script_slug": "event_marked_as_draft"}
        model = self.bc.database.create(monitor_script=monitor_script)

        script = run_script(model.monitor_script)

        del script["slack_payload"]
        del script["text"]

        expected = {
            "severity_level": 5,
            "status": "OPERATIONAL",
            "title": "OK",
        }

        self.assertEqual(script, expected)
        self.assertEqual(
            self.bc.database.list_of("monitoring.MonitorScript"), [{**self.bc.format.to_dict(model.monitor_script)}]
        )

    """
    🔽🔽🔽 With one Event with status ACTIVE
    """

    def test_event_marked_as_draft__one_event__status_active(self):
        """
        Descriptions of models are being generated:

          Academy(id=1):
            city: City(id=1)
            country: Country(code="XLx")

          Application(id=1):
            academy: Academy(id=1)

          Event(id=1):
            academy: Academy(id=1)

          MonitorScript(id=1):
            application: Application(id=1)
        """

        monitor_script = {"script_slug": "event_marked_as_draft"}
        event = {"status": "ACTIVE"}
        model = self.bc.database.create(monitor_script=monitor_script, event=event)

        script = run_script(model.monitor_script)

        del script["slack_payload"]
        del script["text"]

        expected = {
            "severity_level": 5,
            "status": "OPERATIONAL",
            "title": "OK",
        }

        self.assertEqual(script, expected)
        self.assertEqual(
            self.bc.database.list_of("monitoring.MonitorScript"), [{**self.bc.format.to_dict(model.monitor_script)}]
        )

    """
    🔽🔽🔽 With one Event with status DELETED
    """

    def test_event_marked_as_draft__one_event__status_deleted(self):
        """
        Descriptions of models are being generated:

          Academy(id=1):
            city: City(id=1)
            country: Country(code="XLx")

          Application(id=1):
            academy: Academy(id=1)

          Event(id=1):
            academy: Academy(id=1)

          MonitorScript(id=1):
            application: Application(id=1)
        """

        monitor_script = {"script_slug": "event_marked_as_draft"}
        event = {"status": "DELETED"}
        model = self.bc.database.create(monitor_script=monitor_script, event=event)

        script = run_script(model.monitor_script)

        del script["slack_payload"]
        del script["text"]

        expected = {
            "severity_level": 5,
            "status": "OPERATIONAL",
            "title": "OK",
        }

        self.assertEqual(script, expected)
        self.assertEqual(
            self.bc.database.list_of("monitoring.MonitorScript"), [{**self.bc.format.to_dict(model.monitor_script)}]
        )

    """
    🔽🔽🔽 With one Event with status DRAFT
    """

    def test_event_marked_as_draft__one_event__status_draft(self):
        """
        Descriptions of models are being generated:

          Academy(id=1):
            city: City(id=1)
            country: Country(code="XLx")

          Application(id=1):
            academy: Academy(id=1)

          Event(id=1):
            academy: Academy(id=1)

          MonitorScript(id=1):
            application: Application(id=1)
        """

        monitor_script = {"script_slug": "event_marked_as_draft"}
        event = {"status": "DRAFT"}
        model = self.bc.database.create(monitor_script=monitor_script, event=event)

        script = run_script(model.monitor_script)

        del script["slack_payload"]
        del script["text"]

        expected = {
            "btn": {"label": "More details", "url": f"/events/list?location={model.academy.slug}"},
            "severity_level": 100,
            "status": "CRITICAL",
            "error_slug": "draft-events",
            "title": f"There are 1 draft events to published or deleted in {model.academy.name}",
        }

        self.assertEqual(script, expected)
        self.assertEqual(
            self.bc.database.list_of("monitoring.MonitorScript"),
            [
                {
                    **self.bc.format.to_dict(model.monitor_script),
                    "status": "CRITICAL",
                    "status_text": None,
                },
            ],
        )

    """
    🔽🔽🔽 With two Event with status DRAFT
    """

    def test_event_marked_as_draft__two_events__status_draft(self):
        """
        Descriptions of models are being generated:

          Academy(id=1):
            city: City(id=1)
            country: Country(code="XLx")

          Application(id=1):
            academy: Academy(id=1)

          Event(id=1):
            academy: Academy(id=1)

          Event(id=2):
            academy: Academy(id=1)

          MonitorScript(id=1):
            application: Application(id=1)
        """

        monitor_script = {"script_slug": "event_marked_as_draft"}
        event = {"status": "DRAFT"}
        model = self.bc.database.create(monitor_script=monitor_script, event=(2, event))

        script = run_script(model.monitor_script)

        del script["slack_payload"]
        del script["text"]

        expected = {
            "btn": {"label": "More details", "url": f"/events/list?location={model.academy.slug}"},
            "severity_level": 100,
            "status": "CRITICAL",
            "error_slug": "draft-events",
            "title": f"There are 2 draft events to published or deleted in {model.academy.name}",
        }

        self.assertEqual(script, expected)
        self.assertEqual(
            self.bc.database.list_of("monitoring.MonitorScript"),
            [
                {
                    **self.bc.format.to_dict(model.monitor_script),
                    "status": "CRITICAL",
                    "status_text": None,
                },
            ],
        )
