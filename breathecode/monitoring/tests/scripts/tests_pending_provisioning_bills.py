from datetime import timedelta
from django.utils import timezone
from ..mixins import MonitoringTestCase
from breathecode.monitoring.actions import run_script
from breathecode.admissions.models import Cohort, Academy


class AcademyCohortTestSuite(MonitoringTestCase):
    # When: nothing was provided
    # Then: nothing happens
    def test_nothing_provided(self):
        monitor_script = {"script_slug": "pending_provisioning_bills"}
        model = self.bc.database.create(monitor_script=monitor_script)

        script = run_script(model.monitor_script)

        del script["slack_payload"]

        expected = {
            "severity_level": 5,
            "status": "OPERATIONAL",
            "text": "All good\n",
            "title": "OK",
        }

        self.assertEqual(script, expected)
        self.assertEqual(
            self.bc.database.list_of("monitoring.MonitorScript"),
            [
                self.bc.format.to_dict(model.monitor_script),
            ],
        )

    # Given: 1 ProvisioningBill per status and academy and
    #     -> 1 ProvisioningActivity per status and academy
    # When: academy 1 run script
    # Then: nothing to report
    def test_all_right_cases(self):
        provisioning_bill_statuses = ["DUE", "DISPUTED", "IGNORED", "PENDING", "PAID"]
        provisioning_bills = [{"status": s, "academy_id": 1} for s in provisioning_bill_statuses]

        provisioning_activity_statuses = ["PENDING", "PERSISTED"]
        provisioning_activities = [{"status": s, "bill_id": 1} for s in provisioning_activity_statuses]
        provisioning_activities += [{"status": s, "bill_id": None} for s in provisioning_activity_statuses]

        monitor_script = {"script_slug": "pending_provisioning_bills"}
        model = self.bc.database.create(
            monitor_script=monitor_script,
            academy=2,
            provisioning_bill=provisioning_bills,
            provisioning_user_consumption=provisioning_activities,
        )

        script = run_script(model.monitor_script)

        del script["slack_payload"]

        expected = {
            "severity_level": 5,
            "status": "OPERATIONAL",
            "text": "All good\n",
            "title": "OK",
        }

        self.assertEqual(script, expected)
        self.assertEqual(
            self.bc.database.list_of("monitoring.MonitorScript"),
            [
                self.bc.format.to_dict(model.monitor_script),
            ],
        )

    # Given: 1 ProvisioningBill per wrong status and academy and
    #     -> 1 ProvisioningActivity per wrong status and academy
    # When: academy 1 run script
    # Then: report 1 bill and 2 activities with errors
    def test_all_wrong_cases(self):
        provisioning_bill_statuses = ["ERROR"]
        provisioning_bills = [{"status": s, "academy_id": 1} for s in provisioning_bill_statuses]

        provisioning_activity_statuses = ["ERROR"]
        provisioning_activities = [{"status": s, "bill_id": 1} for s in provisioning_activity_statuses]
        provisioning_activities += [{"status": s, "bill_id": None} for s in provisioning_activity_statuses]

        monitor_script = {"script_slug": "pending_provisioning_bills"}
        model = self.bc.database.create(
            monitor_script=monitor_script,
            academy=2,
            provisioning_bill=provisioning_bills,
            provisioning_user_consumption=provisioning_activities,
        )

        script = run_script(model.monitor_script)

        del script["slack_payload"]

        expected = {
            "btn": None,
            "error_slug": "1-bills-and-2-activities-with-errors",
            "severity_level": 100,
            "status": "CRITICAL",
            "text": "There are 1 provisioning bills and 2 provisioning user consumptions with errors",
            "title": "There are 1 bills and 2 user consumptions with errors",
        }

        self.assertEqual(script, expected)
        self.assertEqual(
            self.bc.database.list_of("monitoring.MonitorScript"),
            [
                self.bc.format.to_dict(model.monitor_script),
            ],
        )

    # Given: 1 ProvisioningBill per wrong status and academy 2 and
    #     -> 1 ProvisioningActivity per wrong status and academy 2
    # When: academy 1 run script
    # Then: Don't report anything because the academy is different
    def test_errors_from_other_academies_are_ignored(self):
        provisioning_bill_statuses = ["ERROR"]
        provisioning_bills = [{"status": s, "academy_id": 2} for s in provisioning_bill_statuses]

        provisioning_activity_statuses = ["ERROR"]
        provisioning_activities = [{"status": s, "bill_id": 1} for s in provisioning_activity_statuses]

        monitor_script = {"script_slug": "pending_provisioning_bills"}
        model = self.bc.database.create(
            monitor_script=monitor_script,
            academy=2,
            provisioning_bill=provisioning_bills,
            provisioning_user_consumption=provisioning_activities,
        )

        script = run_script(model.monitor_script)

        del script["slack_payload"]

        expected = {
            "severity_level": 5,
            "status": "OPERATIONAL",
            "text": "All good\n",
            "title": "OK",
        }

        self.assertEqual(script, expected)
        self.assertEqual(
            self.bc.database.list_of("monitoring.MonitorScript"),
            [
                self.bc.format.to_dict(model.monitor_script),
            ],
        )
