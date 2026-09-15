from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from breathecode.payments.models import PlanFinancing
from breathecode.provisioning.tasks import deprovision_plan_financing_third_party


def _financing_with_vps(bc, *, status: str, plan_expires_at):
    return bc.database.create(
        academy=1,
        user=1,
        plan={"is_renewable": False, "time_of_life": 12, "time_of_life_unit": "MONTH"},
        plan_financing={
            "status": status,
            "plan_expires_at": plan_expires_at,
            "valid_until": plan_expires_at,
            "next_payment_at": plan_expires_at,
            "how_many_installments": 1,
            "installments_paid": 1,
        },
        service={"type": "VOID", "slug": "vps_server", "consumer": "VPS_SERVER"},
        service_item={"how_many": 1},
        plan_service_item=True,
    )


@pytest.mark.django_db
@patch("breathecode.provisioning.tasks.deprovision_service")
def test_emits_deprovision_when_fully_paid_and_grace_passed(mock_signal, bc):
    model = _financing_with_vps(
        bc,
        status=PlanFinancing.Status.FULLY_PAID,
        plan_expires_at=timezone.now() - timedelta(days=30),
    )

    deprovision_plan_financing_third_party(model.plan_financing.id)

    mock_signal.send_robust.assert_called_once()
    kwargs = mock_signal.send_robust.call_args.kwargs
    assert kwargs["user_id"] == model.user.id
    assert kwargs["context"]["plan_financing_id"] == model.plan_financing.id
    assert kwargs["context"]["academy_id"] == model.academy.id


@pytest.mark.django_db
@patch("breathecode.provisioning.tasks.deprovision_service")
def test_skips_when_not_fully_paid(mock_signal, bc):
    model = _financing_with_vps(
        bc,
        status=PlanFinancing.Status.ACTIVE,
        plan_expires_at=timezone.now() - timedelta(days=30),
    )

    deprovision_plan_financing_third_party(model.plan_financing.id)

    mock_signal.send_robust.assert_not_called()


@pytest.mark.django_db
@patch("breathecode.provisioning.tasks.deprovision_service")
def test_skips_when_grace_window_is_still_open(mock_signal, bc):
    model = _financing_with_vps(
        bc,
        status=PlanFinancing.Status.FULLY_PAID,
        plan_expires_at=timezone.now() + timedelta(days=30),
    )

    deprovision_plan_financing_third_party(model.plan_financing.id)

    mock_signal.send_robust.assert_not_called()
