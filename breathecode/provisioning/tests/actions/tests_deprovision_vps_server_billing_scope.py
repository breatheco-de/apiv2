"""Tests: VPS deprovision scope by subscription / plan financing (no whole-academy nuclear wipe)."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from dateutil.relativedelta import relativedelta
from django.utils import timezone

from breathecode.payments.models import UNIT, Consumable
from breathecode.provisioning.actions import deprovision_vps_server
from breathecode.provisioning.models import ProvisioningVPS


@pytest.mark.django_db
def test_deprovision_vps_server_only_machines_tied_to_subscription_id(bc):
    """
    Regresión: con subscription_id en el context, solo se encola deprovision de VPS cuyo
    consumed_consumable pertenece a esa suscripción, no otras en la misma academia.
    """
    utc = timezone.now()
    future = utc + relativedelta(months=1)

    model_a = bc.database.create(
        country=1,
        city=1,
        academy=1,
        user=1,
        provisioning_vendor=1,
        subscription={
            "valid_until": future,
            "next_payment_at": future,
            "seat_service_item_id": None,
        },
        plan={"is_renewable": False},
        service={"type": "VOID", "slug": "vps_server"},
        service_item={"service_id": 1, "how_many": 1},
        subscription_service_item={"subscription_id": 1, "service_item_id": 1},
    )
    user = model_a.user
    academy = model_a.academy
    vendor = model_a.provisioning_vendor
    sub_a = model_a.subscription
    si_a = model_a.service_item

    model_b = bc.database.create(
        user=1,
        academy=1,
        subscription={
            "valid_until": future,
            "next_payment_at": future,
            "seat_service_item_id": None,
        },
        plan={"is_renewable": False},
        service_item={"service_id": 1, "how_many": 1},
        subscription_service_item={"subscription_id": 2, "service_item_id": 2},
    )
    sub_b = model_b.subscription
    si_b = model_b.service_item

    c_a = Consumable.objects.create(
        user=user,
        service_item=si_a,
        unit_type=UNIT,
        how_many=0,
        subscription=sub_a,
        valid_until=future,
    )
    c_b = Consumable.objects.create(
        user=user,
        service_item=si_b,
        unit_type=UNIT,
        how_many=0,
        subscription=sub_b,
        valid_until=future,
    )

    vps_a = ProvisioningVPS.objects.create(
        user=user,
        academy=academy,
        vendor=vendor,
        consumed_consumable=c_a,
        status=ProvisioningVPS.VPS_STATUS_ACTIVE,
        provisioned_at=utc,
    )
    vps_b = ProvisioningVPS.objects.create(
        user=user,
        academy=academy,
        vendor=vendor,
        consumed_consumable=c_b,
        status=ProvisioningVPS.VPS_STATUS_ACTIVE,
        provisioned_at=utc,
    )

    with patch("breathecode.provisioning.tasks.deprovision_vps_task") as mock_task:
        deprovision_vps_server(
            user_id=user.id,
            context={
                "academy_id": academy.id,
                "subscription_id": sub_a.id,
            },
        )

    called_ids = {c[0][0] for c in mock_task.delay.call_args_list}
    assert called_ids == {vps_a.id}
    assert vps_b.id not in called_ids


@pytest.mark.django_db
def test_deprovision_vps_server_legacy_academy_only_still_includes_all_pools_in_academy(bc):
    """Sin subscription_id: mismo comportamiento que antes (todos los VPS del usuario en la academia)."""
    utc = timezone.now()
    future = utc + relativedelta(months=1)

    model_a = bc.database.create(
        country=1,
        city=1,
        academy=1,
        user=1,
        provisioning_vendor=1,
        subscription={
            "valid_until": future,
            "next_payment_at": future,
            "seat_service_item_id": None,
        },
        plan={"is_renewable": False},
        service={"type": "VOID", "slug": "vps_server"},
        service_item={"service_id": 1, "how_many": 1},
        subscription_service_item={"subscription_id": 1, "service_item_id": 1},
    )
    user = model_a.user
    academy = model_a.academy
    vendor = model_a.provisioning_vendor
    sub_a = model_a.subscription
    si_a = model_a.service_item

    model_b = bc.database.create(
        user=1,
        academy=1,
        subscription={
            "valid_until": future,
            "next_payment_at": future,
            "seat_service_item_id": None,
        },
        plan={"is_renewable": False},
        service_item={"service_id": 1, "how_many": 1},
        subscription_service_item={"subscription_id": 2, "service_item_id": 2},
    )
    sub_b = model_b.subscription
    si_b = model_b.service_item

    c_a = Consumable.objects.create(
        user=user,
        service_item=si_a,
        unit_type=UNIT,
        how_many=0,
        subscription=sub_a,
        valid_until=future,
    )
    c_b = Consumable.objects.create(
        user=user,
        service_item=si_b,
        unit_type=UNIT,
        how_many=0,
        subscription=sub_b,
        valid_until=future,
    )
    vps_a = ProvisioningVPS.objects.create(
        user=user,
        academy=academy,
        vendor=vendor,
        consumed_consumable=c_a,
        status=ProvisioningVPS.VPS_STATUS_ACTIVE,
        provisioned_at=utc,
    )
    vps_b = ProvisioningVPS.objects.create(
        user=user,
        academy=academy,
        vendor=vendor,
        consumed_consumable=c_b,
        status=ProvisioningVPS.VPS_STATUS_ACTIVE,
        provisioned_at=utc,
    )

    with patch("breathecode.provisioning.tasks.deprovision_vps_task") as mock_task:
        deprovision_vps_server(
            user_id=user.id,
            context={"academy_id": academy.id},
        )

    called_ids = {c[0][0] for c in mock_task.delay.call_args_list}
    assert called_ids == {vps_a.id, vps_b.id}
