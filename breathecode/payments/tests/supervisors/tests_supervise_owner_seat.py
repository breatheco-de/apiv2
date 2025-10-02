"""Tests for the supervisor that ensures the owner seat exists when a billing team is present.

This suite verifies that:
- The supervisor registers and logs a readable message when the owner seat is missing.
- A SupervisorIssue is created with the expected code and params.
- The issue handler returns False when the billing team referenced in params does not exist.
- The issue handler returns True and creates the owner seat when the team exists.
"""

from asgiref.sync import sync_to_async
from breathecode.monitoring.models import Supervisor as SupervisorModel, SupervisorIssue
from breathecode.payments.supervisors import (
    supervise_owner_seat,
    owner_seat_missing,
)
from breathecode.payments.models import SubscriptionBillingTeam, SubscriptionSeat, Plan
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


def test_supervise_owner_seat_detects_and_handler_behaviour(database, bc: Breathecode):
    """Detect missing owner seat and validate handler False/True flows."""
    # Arrange: subscription with billing team and missing owner seat
    model = database.create(user=1, subscription=1, city=1, country=1)
    model.subscription.has_billing_team = True
    model.subscription.save(update_fields=["has_billing_team"])

    team = SubscriptionBillingTeam.objects.create(
        subscription=model.subscription,
        name=f"Team {model.subscription.id}",
        seats_limit=1,
        consumption_strategy=Plan.ConsumptionStrategy.PER_TEAM,
    )

    # Act: detect (decorated supervisor writes issues to DB)
    supervise_owner_seat()

    supervisor = Supervisor(bc)
    # Assert supervisor exists and log created
    assert supervisor.list() == [
        {
            "task_module": "breathecode.payments.supervisors",
            "task_name": "supervise_owner_seat",
        },
    ]
    assert supervisor.log("breathecode.payments.supervisors", "supervise_owner_seat") == [
        f"Owner seat missing for subscription {model.subscription.id}",
    ]

    # Assert detection via DB
    issues = list(SupervisorIssue.objects.all())
    assert len(issues) == 1
    issue = issues[0]
    assert issue.code == "owner-seat-missing"
    params = issue.params or {}
    assert params.get("subscription_id") == model.subscription.id
    assert params.get("team_id") == team.id
    assert params.get("user_id") == model.user.id

    # Act: handler returns False if team missing
    # simulate missing team by altering issue params to point to a non-existent team id
    issue.params = {
        "subscription_id": model.subscription.id,
        "team_id": team.id + 9999,
        "user_id": model.user.id,
        "email": model.user.email,
    }
    issue.save(update_fields=["params"])
    res_missing = owner_seat_missing(issue.id)
    assert res_missing is False

    # Act: handler creates seat and returns True
    # create a new issue with proper params (the previous one was already marked as fixed=False)
    new_issue = SupervisorIssue.objects.create(
        supervisor=issue.supervisor,
        error=f"Owner seat missing for subscription {model.subscription.id}",
        code="owner-seat-missing",
        params={
            "subscription_id": model.subscription.id,
            "team_id": team.id,
            "user_id": model.user.id,
            "email": model.user.email,
        },
    )

    res_ok = owner_seat_missing(new_issue.id)
    assert res_ok is True
    assert SubscriptionSeat.objects.filter(billing_team=team, user=model.user).exists()
