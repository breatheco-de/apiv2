from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from breathecode.payments.models import PlanFinancing, PlanServiceItem, Service, ServiceItem
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


def _attach_plan_service(plan, *, slug: str, consumer: str):
    service = Service.objects.create(slug=slug, type=Service.Type.VOID, consumer=consumer)
    service_item = ServiceItem.objects.create(service=service, how_many=1)
    return PlanServiceItem.objects.create(plan=plan, service_item=service_item)


def _financing_with_third_party_services(bc, *, status: str, plan_expires_at):
    model = _financing_with_vps(bc, status=status, plan_expires_at=plan_expires_at)
    plan = model.plan_financing.plans.first()
    _attach_plan_service(plan, slug="llm-budget", consumer=Service.Consumer.LLM_BUDGET)
    _attach_plan_service(plan, slug="github-copilot", consumer=Service.Consumer.GITHUB_COPILOT)
    return model


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


@pytest.mark.django_db
@patch("breathecode.provisioning.tasks.deprovision_service")
def test_emits_all_third_party_services_and_keeps_fully_paid(mock_signal, bc):
    """After grace: VPS/LLM/Copilot get deprovision_service; financing stays FULLY_PAID."""
    model = _financing_with_third_party_services(
        bc,
        status=PlanFinancing.Status.FULLY_PAID,
        plan_expires_at=timezone.now() - timedelta(days=30),
    )

    with patch("breathecode.provisioning.actions.get_service_deprovisioner", return_value=lambda **kwargs: None):
        deprovision_plan_financing_third_party(model.plan_financing.id)

    assert mock_signal.send_robust.call_count == 3
    emitted_slugs = {call.kwargs["instance"].slug for call in mock_signal.send_robust.call_args_list}
    assert emitted_slugs == {"vps_server", "llm-budget", "github-copilot"}
    for call in mock_signal.send_robust.call_args_list:
        assert call.kwargs["user_id"] == model.user.id
        assert call.kwargs["context"]["plan_financing_id"] == model.plan_financing.id
        assert call.kwargs["context"]["academy_id"] == model.academy.id

    model.plan_financing.refresh_from_db()
    assert model.plan_financing.status == PlanFinancing.Status.FULLY_PAID
