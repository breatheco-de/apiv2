"""Tests for supervisor detecting ACTIVE plan financings that should be FULLY_PAID."""

from unittest.mock import patch

from asgiref.sync import sync_to_async
from breathecode.monitoring.models import Supervisor as SupervisorModel, SupervisorIssue
from breathecode.payments.models import PlanFinancing
from breathecode.payments.supervisors import (
    plan_financing_fully_paid_drift,
    supervise_active_plan_financing_fully_paid_drift,
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


def test_supervise_active_plan_financing_fully_paid_drift(database, bc: Breathecode):
    model = database.create(user=1, academy=1, plan=1)
    plan_financing = PlanFinancing.objects.create(
        user=model.user,
        academy=model.academy,
        monthly_price=15000,
        how_many_installments=1,
        installments_paid=1,
        status=PlanFinancing.Status.ACTIVE,
        valid_until=model.user.date_joined,
        next_payment_at=model.user.date_joined,
        plan_expires_at=model.user.date_joined,
        currency=model.academy.main_currency,
    )
    plan_financing.plans.add(model.plan)

    supervise_active_plan_financing_fully_paid_drift()

    supervisor = Supervisor(bc)
    assert supervisor.list() == [
        {
            "task_module": "breathecode.payments.supervisors",
            "task_name": "supervise_active_plan_financing_fully_paid_drift",
        },
    ]
    assert supervisor.log(
        "breathecode.payments.supervisors",
        "supervise_active_plan_financing_fully_paid_drift",
    ) == [
        f"PlanFinancing {plan_financing.id} for user {model.user.email} is ACTIVE "
        f"but installments_paid (1) >= how_many_installments (1)",
    ]

    issues = list(SupervisorIssue.objects.all())
    assert len(issues) == 1
    issue = issues[0]
    assert issue.code == "plan-financing-fully-paid-drift"
    assert issue.params == {"plan_financing_id": plan_financing.id}

    with patch("breathecode.payments.supervisors.charge_plan_financing.delay") as mock_charge:
        res = plan_financing_fully_paid_drift(issue.id)
        mock_charge.assert_called_once_with(plan_financing.id)

    assert res is None
