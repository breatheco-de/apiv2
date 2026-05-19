"""Tests for standalone consumable duration, scheduling, and entitlement helper."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from dateutil.relativedelta import relativedelta
from django.utils import timezone

from breathecode.payments import actions
from breathecode.payments.models import UNIT, Consumable, Service


@patch("breathecode.payments.actions.get_service_deprovisioner", return_value=None)
def test_resolve_grant_valid_until_returns_none_without_fields(_mock):
    service = Service(slug="vps_server", type=Service.Type.VOID)
    assert actions.resolve_grant_valid_until(None, None, "en", service) is None


@patch("breathecode.payments.actions.get_service_deprovisioner")
def test_resolve_grant_valid_until_requires_duration_when_deprovisioner(mock_get_deprovisioner):
    mock_get_deprovisioner.return_value = lambda **kwargs: None
    service = Service(slug="vps_server", type=Service.Type.VOID)
    with pytest.raises(Exception) as exc:
        actions.resolve_grant_valid_until(None, None, "en", service)
    assert getattr(exc.value, "slug", None) == "duration-required-for-deprovisioned-service"


@patch("breathecode.payments.actions.get_service_deprovisioner", return_value=None)
def test_resolve_grant_valid_until_duration_and_unit(_mock):
    service = Service(slug="mentorship", type=Service.Type.MENTORSHIP_SERVICE_SET)
    valid_until = actions.resolve_grant_valid_until(2, "week", "en", service)
    assert valid_until is not None
    assert valid_until > timezone.now() + relativedelta(days=10)


def test_resolve_grant_valid_until_requires_both_fields():
    service = Service(slug="vps_server", type=Service.Type.VOID)
    with pytest.raises(Exception) as exc:
        actions.resolve_grant_valid_until(None, "MONTH", "en", service)
    assert getattr(exc.value, "slug", None) == "incomplete-duration"


def test_resolve_grant_valid_until_invalid_unit():
    service = Service(slug="vps_server", type=Service.Type.VOID)
    with pytest.raises(Exception) as exc:
        actions.resolve_grant_valid_until(1, "INVALID", "en", service)
    assert getattr(exc.value, "slug", None) == "invalid-duration-unit"


@patch("breathecode.payments.actions.get_service_deprovisioner")
def test_resolve_grant_valid_until_subtracts_hour_with_deprovisioner(mock_get_deprovisioner):
    mock_get_deprovisioner.return_value = lambda **kwargs: None
    service = Service(slug="vps_server", type=Service.Type.VOID)
    utc = timezone.now()
    valid_until = actions.resolve_grant_valid_until(30, "DAY", "en", service)
    expected = utc + timedelta(days=30) - timedelta(hours=1)
    assert abs((valid_until - expected).total_seconds()) < 5


@patch("breathecode.payments.actions.get_service_deprovisioner", return_value=None)
def test_resolve_grant_valid_until_unchanged_without_deprovisioner(_mock):
    service = Service(slug="vps_server", type=Service.Type.VOID)
    valid_until = actions.resolve_grant_valid_until(1, "MONTH", "en", service)
    assert valid_until is not None
    assert valid_until > timezone.now() + relativedelta(days=25)


@pytest.mark.django_db
def test_user_has_service_entitlement_in_academy_includes_standalone(bc):
    utc = timezone.now()
    future = utc + relativedelta(months=1)
    model = bc.database.create(
        country=1,
        city=1,
        academy=1,
        user=1,
        service={"type": "VOID", "slug": "free-monthly-llm-budget", "consumer": "MONTHLY_LLM_BUDGET"},
        service_item={"service_id": 1, "how_many": 1},
        bag={"academy_id": 1, "user_id": 1},
        invoice={"bag_id": 1, "user_id": 1, "academy_id": 1},
    )
    consumable = Consumable.objects.create(
        user=model.user,
        service_item=model.service_item,
        unit_type=UNIT,
        how_many=1,
        standalone_invoice=model.invoice,
        valid_until=future,
    )
    assert actions.user_has_service_entitlement_in_academy(
        model.user,
        model.service,
        model.academy.id,
    )

    consumable.valid_until = utc - timedelta(hours=1)
    consumable.save(update_fields=["valid_until"])
    assert not actions.user_has_service_entitlement_in_academy(
        model.user,
        model.service,
        model.academy.id,
    )


@patch("breathecode.payments.actions.schedule_task")
@patch("breathecode.payments.actions.get_service_deprovisioner", return_value=None)
def test_schedule_standalone_consumable_deprovision_skips_without_deprovisioner(
    _mock_get_deprovisioner,
    mock_schedule_task,
):
    service = MagicMock()
    service.slug = "vps_server"
    service.type = Service.Type.VOID
    valid_until = timezone.now() + timedelta(days=10)
    actions.schedule_standalone_consumable_deprovision(99, valid_until, service)
    mock_schedule_task.assert_not_called()


@patch("breathecode.payments.actions.schedule_task")
def test_schedule_standalone_consumable_deprovision_enqueues_for_vps(mock_schedule_task):
    service = Service(slug="vps_server", type=Service.Type.VOID, consumer=Service.Consumer.VPS_SERVER)
    valid_until = timezone.now() + timedelta(days=10)
    manager = MagicMock()
    mock_schedule_task.return_value = manager

    with patch(
        "breathecode.payments.actions.get_service_deprovisioner",
        return_value=lambda **kwargs: None,
    ):
        actions.schedule_standalone_consumable_deprovision(42, valid_until, service)

    mock_schedule_task.assert_called_once()
    manager.call.assert_called_once_with(42)
