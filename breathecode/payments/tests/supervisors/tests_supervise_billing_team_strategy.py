"""Tests for the supervisor that detects billing team strategy drift.

This suite verifies that:
- The supervisor registers itself and logs a readable message when a team strategy
  differs from the plan's effective strategy.
- A SupervisorIssue is stored with the expected code and params.
- The issue handler updates the team strategy, schedules a rebuild, and returns None
  (scheduled -> supervisor should reattempt later).
"""

import pytest
from unittest.mock import MagicMock, call

from asgiref.sync import sync_to_async
from breathecode.monitoring.models import Supervisor as SupervisorModel, SupervisorIssue
from breathecode.payments.supervisors import (
    supervise_billing_team_strategy,
    billing_team_strategy_mismatch,
)
from breathecode.payments.models import SubscriptionBillingTeam, Plan
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode


@pytest.fixture(autouse=True)
def patch_tasks(monkeypatch):
    # Patch scheduler task used by handler
    from breathecode.payments import supervisors as sup

    monkeypatch.setattr(sup.build_service_stock_scheduler_from_subscription, "delay", MagicMock(), raising=False)
    return sup


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


@pytest.fixture
def supervisor(db, bc: Breathecode):
    yield Supervisor(bc)


def test_supervise_billing_team_strategy_detects_and_handler_schedules(database, patch_tasks, supervisor):
    """Detect strategy drift and ensure handler schedules rebuild and returns None."""
    # Arrange: subscription with plan PER_TEAM and team with PER_SEAT (mismatch)
    plan = {"is_renewable": False, "trial_duration": 0, "consumption_strategy": "PER_TEAM"}
    model = database.create(user=1, subscription=1, plan=plan, city=1, country=1)

    team = SubscriptionBillingTeam.objects.create(
        subscription=model.subscription,
        name=f"Team {model.subscription.id}",
        seats_limit=1,
        consumption_strategy=Plan.ConsumptionStrategy.PER_SEAT,
    )

    # Act: detect (decorated supervisor writes issues to DB)
    supervise_billing_team_strategy()

    # Assert supervisor is registered and message logged
    assert supervisor.list() == [
        {
            "task_module": "breathecode.payments.supervisors",
            "task_name": "supervise_billing_team_strategy",
        },
    ]

    expected_msg = f"Team {team.id} strategy {Plan.ConsumptionStrategy.PER_SEAT} != {Plan.ConsumptionStrategy.PER_TEAM}"
    assert supervisor.log("breathecode.payments.supervisors", "supervise_billing_team_strategy") == [expected_msg]

    # Assert detection via DB
    issues = list(SupervisorIssue.objects.all())
    assert len(issues) == 1
    issue = issues[0]
    assert issue.code == "billing-team-strategy-mismatch"
    params = issue.params or {}
    assert params.get("subscription_id") == model.subscription.id
    assert params.get("team_id") == team.id
    assert params.get("expected_strategy") == "PER_TEAM"
    assert params.get("current_strategy") == "PER_SEAT"

    # Act: fix via handler
    result = billing_team_strategy_mismatch(issue.id)

    # Assert: scheduled (None), team updated, scheduler rebuild queued
    assert result is None
    issue.refresh_from_db()
    assert issue.fixed is None
    team.refresh_from_db()
    assert team.consumption_strategy == Plan.ConsumptionStrategy.PER_TEAM
    assert patch_tasks.build_service_stock_scheduler_from_subscription.delay.call_args_list == [
        call(model.subscription.id)
    ]
