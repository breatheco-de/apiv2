"""Tests for power_off_plan_financing_third_party (no schedule)."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from breathecode.payments.models import PlanFinancing, PlanServiceItem, Service, ServiceItem
from breathecode.provisioning.tasks import power_off_plan_financing_third_party


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


def _power_off_for_vps_only(handler):
    return lambda slug: handler if slug == "vps_server" else None


@pytest.mark.django_db
def test_calls_power_off_when_fully_paid_and_window_passed(bc):
    model = _financing_with_vps(
        bc,
        status=PlanFinancing.Status.FULLY_PAID,
        plan_expires_at=timezone.now() - timedelta(days=30),
    )
    handler = MagicMock()

    with patch(
        "breathecode.provisioning.actions.get_service_power_off",
        side_effect=_power_off_for_vps_only(handler),
    ):
        power_off_plan_financing_third_party(model.plan_financing.id)

    handler.assert_called_once_with(
        user_id=model.user.id,
        context={
            "academy_id": model.academy.id,
            "plan_financing_id": model.plan_financing.id,
        },
    )


@pytest.mark.django_db
def test_skips_when_not_fully_paid(bc):
    model = _financing_with_vps(
        bc,
        status=PlanFinancing.Status.ACTIVE,
        plan_expires_at=timezone.now() - timedelta(days=30),
    )
    handler = MagicMock()

    with patch(
        "breathecode.provisioning.actions.get_service_power_off",
        side_effect=_power_off_for_vps_only(handler),
    ):
        power_off_plan_financing_third_party(model.plan_financing.id)

    handler.assert_not_called()


@pytest.mark.django_db
def test_skips_when_power_off_window_is_still_open(bc):
    model = _financing_with_vps(
        bc,
        status=PlanFinancing.Status.FULLY_PAID,
        plan_expires_at=timezone.now() + timedelta(days=30),
    )
    handler = MagicMock()

    with patch(
        "breathecode.provisioning.actions.get_service_power_off",
        side_effect=_power_off_for_vps_only(handler),
    ):
        power_off_plan_financing_third_party(model.plan_financing.id)

    handler.assert_not_called()


@pytest.mark.django_db
def test_skips_llm_and_copilot_keeps_fully_paid(bc):
    """Only services with @service_power_off run; LLM/Copilot have none. Status stays FULLY_PAID."""
    model = _financing_with_third_party_services(
        bc,
        status=PlanFinancing.Status.FULLY_PAID,
        plan_expires_at=timezone.now() - timedelta(days=30),
    )
    handler = MagicMock()

    with patch(
        "breathecode.provisioning.actions.get_service_power_off",
        side_effect=_power_off_for_vps_only(handler),
    ):
        power_off_plan_financing_third_party(model.plan_financing.id)

    handler.assert_called_once()
    assert handler.call_args.kwargs["context"]["plan_financing_id"] == model.plan_financing.id
    model.plan_financing.refresh_from_db()
    assert model.plan_financing.status == PlanFinancing.Status.FULLY_PAID
