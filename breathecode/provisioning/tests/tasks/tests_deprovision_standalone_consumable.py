"""Tests for deprovision_standalone_consumable scheduled expiry task."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from breathecode.payments.models import UNIT, Consumable, Service
from breathecode.provisioning.models import ProvisioningVPS
from breathecode.provisioning.tasks import deprovision_standalone_consumable


def _valid_until_at_deprovision_time(utc_now):
    """Consumable ``valid_until`` at grant already includes the 1h buffer; task runs when it is due."""
    return utc_now - timedelta(minutes=5)


@pytest.mark.django_db
@patch("breathecode.provisioning.tasks.deprovision_service")
def test_deprovision_standalone_consumable_vps_sends_provisioning_vps_ids(mock_signal, bc):
    utc = timezone.now()
    future = _valid_until_at_deprovision_time(utc)
    model = bc.database.create(
        country=1,
        city=1,
        academy=1,
        user=1,
        provisioning_vendor=1,
        service={"type": "VOID", "slug": "vps_server", "consumer": "VPS_SERVER"},
        service_item={"service_id": 1, "how_many": 1},
        bag={"academy_id": 1, "user_id": 1},
        invoice={"bag_id": 1, "user_id": 1, "academy_id": 1},
    )
    consumable = Consumable.objects.create(
        user=model.user,
        service_item=model.service_item,
        unit_type=UNIT,
        how_many=0,
        standalone_invoice=model.invoice,
        valid_until=future,
    )
    vps = ProvisioningVPS.objects.create(
        user=model.user,
        academy=model.academy,
        vendor=model.provisioning_vendor,
        consumed_consumable=consumable,
        status=ProvisioningVPS.VPS_STATUS_ACTIVE,
    )

    deprovision_standalone_consumable(consumable.id)

    mock_signal.send_robust.assert_called_once()
    kwargs = mock_signal.send_robust.call_args.kwargs
    assert kwargs["user_id"] == model.user.id
    assert kwargs["context"]["provisioning_vps_ids"] == [vps.id]


@pytest.mark.django_db
@patch("breathecode.provisioning.tasks.deprovision_service")
def test_deprovision_standalone_consumable_llm_sends_academy_id(mock_signal, bc):
    utc = timezone.now()
    future = _valid_until_at_deprovision_time(utc)
    model = bc.database.create(
        country=1,
        city=1,
        academy=1,
        user=1,
        service={
            "type": "VOID",
            "slug": "free-monthly-llm-budget",
            "consumer": "MONTHLY_LLM_BUDGET",
        },
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

    deprovision_standalone_consumable(consumable.id)

    mock_signal.send_robust.assert_called_once()
    kwargs = mock_signal.send_robust.call_args.kwargs
    assert kwargs["context"] == {"academy_id": model.academy.id}


@pytest.mark.django_db
@patch("breathecode.provisioning.tasks.deprovision_service")
def test_deprovision_standalone_consumable_vps_noop_without_vps(mock_signal, bc):
    utc = timezone.now()
    future = _valid_until_at_deprovision_time(utc)
    model = bc.database.create(
        country=1,
        city=1,
        academy=1,
        user=1,
        service={"type": "VOID", "slug": "vps_server", "consumer": "VPS_SERVER"},
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

    deprovision_standalone_consumable(consumable.id)

    mock_signal.send_robust.assert_not_called()


@pytest.mark.django_db
@patch("breathecode.provisioning.tasks.deprovision_service")
def test_deprovision_standalone_consumable_skips_without_valid_until(mock_signal, bc):
    utc = timezone.now()
    model = bc.database.create(
        country=1,
        city=1,
        academy=1,
        user=1,
        service={
            "type": "VOID",
            "slug": "free-monthly-llm-budget",
            "consumer": "MONTHLY_LLM_BUDGET",
        },
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
        valid_until=None,
    )

    deprovision_standalone_consumable(consumable.id)

    mock_signal.send_robust.assert_not_called()


@pytest.mark.django_db
@patch("breathecode.provisioning.tasks.payment_actions.schedule_standalone_consumable_deprovision")
@patch("breathecode.provisioning.tasks.deprovision_service")
def test_deprovision_standalone_consumable_reschedules_when_valid_until_in_future(
    mock_signal,
    mock_schedule,
    bc,
):
    utc = timezone.now()
    future = utc + timedelta(days=30)
    model = bc.database.create(
        country=1,
        city=1,
        academy=1,
        user=1,
        service={
            "type": "VOID",
            "slug": "free-monthly-llm-budget",
            "consumer": "MONTHLY_LLM_BUDGET",
        },
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

    deprovision_standalone_consumable(consumable.id)

    mock_signal.send_robust.assert_not_called()
    mock_schedule.assert_called_once_with(consumable.id, future, model.service)
