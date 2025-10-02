"""Tests for the supervisor that detects has_billing_team flag drift.

This suite verifies that:
- The supervisor is registered and writes a readable log when drift is detected.
- A SupervisorIssue with code `billing-team-flag-drift` is stored with expected params.
- The issue handler normalizes the flag and returns True.
"""

from asgiref.sync import sync_to_async
from breathecode.monitoring.models import Supervisor as SupervisorModel, SupervisorIssue
from breathecode.payments.supervisors import (
    supervise_billing_team_flag_drift,
    billing_team_flag_drift,
)
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode


class Supervisor:

    def __init__(self, bc: Breathecode):
        self._bc = bc

    def list(self):
        supervisors = SupervisorModel.objects.all()
        return [
            {
                "task_module": supervisor.task_module,
                "task_name": supervisor.task_name,
            }
            for supervisor in supervisors
        ]

    @sync_to_async
    def alist(self):
        return self.list()

    def log(self, module, name):
        issues = SupervisorIssue.objects.filter(supervisor__task_module=module, supervisor__task_name=name)
        return [x.error for x in issues]

    @sync_to_async
    def alog(self, module, name):
        return self.log(module, name)


def test_supervise_billing_team_flag_drift_detects_and_fixes__has_flag_but_no_team(database, bc: Breathecode):
    """Detect drift (has_billing_team=True, no team) and ensure handler normalizes flag to False."""
    # Arrange: subscription with has_billing_team True but no team exists
    model = database.create(user=1, subscription=1, city=1, country=1)
    model.subscription.has_billing_team = True
    model.subscription.save(update_fields=["has_billing_team"])

    # Act: detect (decorated supervisor writes issues to DB)
    supervise_billing_team_flag_drift()

    supervisor = Supervisor(bc)
    # Assert supervisor exists and log created
    assert supervisor.list() == [
        {
            "task_module": "breathecode.payments.supervisors",
            "task_name": "supervise_billing_team_flag_drift",
        },
    ]

    # Assert detection via DB
    issues = list(SupervisorIssue.objects.all())
    assert len(issues) == 1
    issue = issues[0]
    assert issue.code == "billing-team-flag-drift"
    params = issue.params or {}
    assert params.get("subscription_id") == model.subscription.id
    assert params.get("expected") is False
    assert params.get("current") is True

    # Act: fix flag
    res = billing_team_flag_drift(issue.id)
    assert res is True
    model.subscription.refresh_from_db()
    assert model.subscription.has_billing_team is False
