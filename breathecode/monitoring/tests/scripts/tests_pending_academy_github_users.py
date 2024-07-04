from datetime import timedelta
from django.utils import timezone
from ..mixins import MonitoringTestCase
from breathecode.monitoring.actions import run_script
from breathecode.admissions.models import Cohort, Academy


class AcademyCohortTestSuite(MonitoringTestCase):
    # When: nothing was provided
    # Then: nothing happens
    def test_nothing_provided(self):
        monitor_script = {"script_slug": "pending_academy_github_users"}
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

    # Given: 4 GithubAcademyUser
    # When: academy 1 run script and 2 are marked as add and 2 as delete
    # Then: Don't report anything because the academy is different
    def test_all_right_cases(self):
        github_academy_users = [{"storage_action": "ADD"} for _ in range(2)]
        github_academy_users += [{"storage_action": "DELETE"} for _ in range(2)]
        monitor_script = {"script_slug": "pending_academy_github_users"}
        model = self.bc.database.create(
            monitor_script=monitor_script, academy=1, github_academy_user=github_academy_users
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

    # Given: 4 GithubAcademyUser
    # When: academy 1 run script and 2 are marked as invite and 2 as ignore
    # Then: Don't report anything because the academy is different
    def test_all_wrong_cases(self):
        github_academy_users = [{"storage_action": "INVITE"} for _ in range(2)]
        github_academy_users += [{"storage_action": "IGNORE"} for _ in range(2)]
        monitor_script = {"script_slug": "pending_academy_github_users"}
        model = self.bc.database.create(
            monitor_script=monitor_script, academy=1, github_academy_user=github_academy_users
        )

        script = run_script(model.monitor_script)

        del script["slack_payload"]

        expected = {
            "btn": None,
            "error_slug": "2-invite-and-2-ignore",
            "severity_level": 100,
            "status": "CRITICAL",
            "text": "There are 2 github users marked as invite and 2 marked as ignore",
            "title": "There are 2 github users marked as invite and 2 marked as ignore",
        }

        self.assertEqual(script, expected)
        self.assertEqual(
            self.bc.database.list_of("monitoring.MonitorScript"),
            [
                self.bc.format.to_dict(model.monitor_script),
            ],
        )

    # Given: 4 GithubAcademyUser from other academy
    # When: academy 1 run script and 2 are marked as invite and 2 as ignore
    # Then: Don't report anything because the academy is different
    def test_errors_from_other_academies_are_ignored(self):
        github_academy_users = [{"storage_action": "INVITE", "academy_id": 2} for _ in range(2)]
        github_academy_users += [{"storage_action": "IGNORE", "academy_id": 2} for _ in range(2)]
        monitor_script = {"script_slug": "pending_academy_github_users"}
        model = self.bc.database.create(
            monitor_script=monitor_script, academy=2, github_academy_user=github_academy_users
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
