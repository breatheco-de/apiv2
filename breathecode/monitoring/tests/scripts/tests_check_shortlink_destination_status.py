import datetime
from ..mixins import MonitoringTestCase
from breathecode.monitoring.actions import run_script


class ShortLinkTestSuite(MonitoringTestCase):

    def tests_send_list_of_shortlinks_when_operational(self):
        """
        Checking to see if shortlink script runs with properly with working shortlinks
        """

        monitor_script_kwargs = {"script_slug": "check_shortlinks_with_destination_status_error"}

        model = self.generate_models(academy=True, monitor_script=True, monitor_script_kwargs=monitor_script_kwargs)

        script = run_script(model.monitor_script)

        del script["slack_payload"]

        expected = {
            "severity_level": 5,
            "status": "OPERATIONAL",
            "text": "All shortlinks working properly\n",
            "title": "OK",
        }

        self.assertEqual(script, expected)
        self.assertEqual(
            self.all_monitor_script_dict(),
            [
                {
                    **self.model_to_dict(model, "monitor_script"),
                }
            ],
        )

    def tests_send_list_of_shortlinks_when_operational_with_shortlink_model(self):
        """
        Checking to see if any ShortLink has destination status = 'ERROR'
        """

        monitor_script_kwargs = {"script_slug": "check_shortlinks_with_destination_status_error"}

        model = self.generate_models(
            academy=True, monitor_script=True, short_link=True, monitor_script_kwargs=monitor_script_kwargs
        )

        script = run_script(model.monitor_script)

        del script["slack_payload"]

        expected = {
            "severity_level": 5,
            "status": "OPERATIONAL",
            "text": "All shortlinks working properly\n",
            "title": "OK",
        }

        self.assertEqual(script, expected)
        self.assertEqual(
            self.all_monitor_script_dict(),
            [
                {
                    **self.model_to_dict(model, "monitor_script"),
                }
            ],
        )

    def tests_send_list_of_shortlinks_when_destination_status_error(self):
        """
        Checking to see if any ShortLink has destination status = 'ERROR'
        """

        monitor_script_kwargs = {"script_slug": "check_shortlinks_with_destination_status_error"}

        short_link_kwargs = {"destination_status": "ERROR"}

        model = self.generate_models(
            academy=True,
            monitor_script=True,
            short_link=True,
            short_link_kwargs=short_link_kwargs,
            monitor_script_kwargs=monitor_script_kwargs,
        )

        db = self.model_to_dict(model, "monitor_script")

        script = run_script(model.monitor_script)

        del script["slack_payload"]

        expected = {
            "btn": None,
            "severity_level": 5,
            "title": None,
            "error_slug": "short-link-bad-destination-status",
            "status": "MINOR",
            "text": f"These shortlinks: - URL: {model.short_link.destination} Status: "
            f"{model.short_link.destination_status} Last clicked: never are not working properly.",
        }

        self.assertEqual(script, expected)
        db_values = self.all_monitor_script_dict()
        self.assertDatetime(db_values[0]["last_run"])
        del db_values[0]["last_run"]
        del db["last_run"]
        self.assertEqual(
            db_values,
            [
                {
                    **db,
                    "status": "MINOR",
                    "response_text": f"These shortlinks: - URL: {model.short_link.destination} Status: "
                    f"{model.short_link.destination_status} Last clicked: never are not working properly.",
                    "status_code": 1,
                }
            ],
        )

    def tests_send_list_of_shortlinks_when_destination_status_not_found(self):
        """
        Checking to see if any ShortLink has destination status = 'NOT_FOUND'
        """

        monitor_script_kwargs = {"script_slug": "check_shortlinks_with_destination_status_error"}

        short_link_kwargs = {"destination_status": "NOT_FOUND"}

        model = self.generate_models(
            academy=True,
            monitor_script=True,
            short_link=True,
            short_link_kwargs=short_link_kwargs,
            monitor_script_kwargs=monitor_script_kwargs,
        )

        db = self.model_to_dict(model, "monitor_script")

        script = run_script(model.monitor_script)

        del script["slack_payload"]

        expected = {
            "btn": None,
            "severity_level": 5,
            "title": None,
            "error_slug": "short-link-bad-destination-status",
            "status": "MINOR",
            "text": f"These shortlinks: - URL: {model.short_link.destination} Status: "
            f"{model.short_link.destination_status} Last clicked: never are not working properly.",
        }

        self.assertEqual(script, expected)
        db_values = self.all_monitor_script_dict()
        self.assertDatetime(db_values[0]["last_run"])
        del db_values[0]["last_run"]
        del db["last_run"]
        self.assertEqual(
            db_values,
            [
                {
                    **db,
                    "status": "MINOR",
                    "response_text": f"These shortlinks: - URL: {model.short_link.destination} Status: "
                    f"{model.short_link.destination_status} Last clicked: never are not working properly.",
                    "status_code": 1,
                }
            ],
        )

    def tests_send_list_of_shortlinks_when_destination_status_error_with_lastclick_at(self):
        """
        Checking to see if any ShortLink has destination_status = 'ERROR' with lastclick_at information
        """

        monitor_script_kwargs = {"script_slug": "check_shortlinks_with_destination_status_error"}

        dt = datetime.datetime.now()

        short_link_kwargs = {"destination_status": "ERROR", "lastclick_at": dt}

        model = self.generate_models(
            academy=True,
            monitor_script=True,
            short_link=True,
            short_link_kwargs=short_link_kwargs,
            monitor_script_kwargs=monitor_script_kwargs,
        )

        db = self.model_to_dict(model, "monitor_script")

        script = run_script(model.monitor_script)

        del script["slack_payload"]

        expected = {
            "btn": None,
            "severity_level": 5,
            "title": None,
            "error_slug": "short-link-bad-destination-status",
            "status": "MINOR",
            "text": f"These shortlinks: - URL: {model.short_link.destination} Status: "
            f"{model.short_link.destination_status} Last clicked: "
            f'{model.short_link.lastclick_at.strftime("%m/%d/%Y, %H:%M:%S")} are not working properly.',
        }

        self.assertEqual(script, expected)
        db_values = self.all_monitor_script_dict()
        self.assertDatetime(db_values[0]["last_run"])
        del db_values[0]["last_run"]
        del db["last_run"]

        self.assertEqual(
            db_values,
            [
                {
                    **db,
                    "status": "MINOR",
                    "response_text": f"These shortlinks: - URL: {model.short_link.destination} Status: "
                    f'{model.short_link.destination_status} Last clicked: {model.short_link.lastclick_at.strftime("%m/%d/%Y, %H:%M:%S")} are not working properly.',
                    "status_code": 1,
                }
            ],
        )

    def tests_send_list_of_shortlinks_when_destination_status_not_found_with_lastclick_at(self):
        """
        Checking to see if any ShortLink has destination_status = 'NOT_FOUND' with lastclick_at information
        """

        monitor_script_kwargs = {"script_slug": "check_shortlinks_with_destination_status_error"}

        dt = datetime.datetime.now()

        short_link_kwargs = {"destination_status": "NOT_FOUND", "lastclick_at": dt}

        model = self.generate_models(
            academy=True,
            monitor_script=True,
            short_link=True,
            short_link_kwargs=short_link_kwargs,
            monitor_script_kwargs=monitor_script_kwargs,
        )

        db = self.model_to_dict(model, "monitor_script")

        script = run_script(model.monitor_script)

        del script["slack_payload"]

        expected = {
            "btn": None,
            "severity_level": 5,
            "title": None,
            "error_slug": "short-link-bad-destination-status",
            "status": "MINOR",
            "text": f"These shortlinks: - URL: {model.short_link.destination} Status: "
            f"{model.short_link.destination_status} Last clicked: "
            f'{model.short_link.lastclick_at.strftime("%m/%d/%Y, %H:%M:%S")} are not working properly.',
        }

        self.assertEqual(script, expected)
        db_values = self.all_monitor_script_dict()
        self.assertDatetime(db_values[0]["last_run"])
        del db_values[0]["last_run"]
        del db["last_run"]

        self.assertEqual(
            db_values,
            [
                {
                    **db,
                    "status": "MINOR",
                    "response_text": f"These shortlinks: - URL: {model.short_link.destination} Status: "
                    f'{model.short_link.destination_status} Last clicked: {model.short_link.lastclick_at.strftime("%m/%d/%Y, %H:%M:%S")} are not working properly.',
                    "status_code": 1,
                }
            ],
        )
