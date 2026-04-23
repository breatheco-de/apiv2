"""Tests para ``apply_early_vps_billing_alignment`` (adelanto de ``next_payment_at`` por uso temprano de VPS)."""

from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from dateutil.relativedelta import relativedelta
from django.utils import timezone

from breathecode.payments.models import UNIT, Consumable
from breathecode.provisioning.actions import (
    EARLY_USE_AFTER_CONSUMABLE_CREATION,
    NEXT_CHARGE_PULL_FORWARD,
    apply_early_vps_billing_alignment,
)
from breathecode.provisioning.models import ProvisioningVPS


def _patch_reschedule():
    return patch(
        "breathecode.payments.actions.reschedule_billing_after_vps_next_payment_pull_forward",
        MagicMock(),
    )


def _patch_consumable_lookup_for_vps(vps: ProvisioningVPS, *, created_at):
    """``Consumable`` no expone ``created_at`` en el ORM; fijamos el instante que lee ``apply_early``."""
    c = vps.consumed_consumable
    stub = SimpleNamespace(
        id=c.id,
        created_at=created_at,
        subscription_id=c.subscription_id,
        plan_financing_id=c.plan_financing_id,
        service_item_id=c.service_item_id,
        service_item=c.service_item,
    )
    qs = MagicMock()
    qs.select_related.return_value = qs
    qs.only.return_value = qs
    qs.first.return_value = stub
    return patch("breathecode.provisioning.actions.Consumable.objects.filter", return_value=qs)


@pytest.mark.django_db
def test_apply_early_pulls_plan_financing_next_payment_within_12h_window(bc):
    utc = timezone.now()
    next_payment = utc + relativedelta(months=1)
    model = bc.database.create(
        country=1,
        city=1,
        academy=1,
        user=1,
        provisioning_vendor=1,
        plan_financing={
            "next_payment_at": next_payment,
            "valid_until": utc + relativedelta(months=6),
            "plan_expires_at": utc + relativedelta(years=1),
            "monthly_price": 100,
            "status": "ACTIVE",
            "next_charge_pull_applied": False,
        },
        service={"type": "VOID"},
        service_item={"service_id": 1, "how_many": 1, "third_party_billing_cycle": True},
    )
    si = model.service_item
    pf = model.plan_financing
    future = utc + relativedelta(months=2)
    c = Consumable.objects.create(
        user=model.user,
        service_item=si,
        unit_type=UNIT,
        how_many=1,
        plan_financing=pf,
        valid_until=future,
    )
    created_at = utc - timedelta(hours=6)
    provisioned_at = created_at + timedelta(hours=1)

    vps = ProvisioningVPS.objects.create(
        user=model.user,
        academy=model.academy,
        vendor=model.provisioning_vendor,
        consumed_consumable=c,
        status=ProvisioningVPS.VPS_STATUS_ACTIVE,
        provisioned_at=provisioned_at,
    )

    with _patch_reschedule(), _patch_consumable_lookup_for_vps(vps, created_at=created_at):
        apply_early_vps_billing_alignment(vps)

    pf.refresh_from_db()
    assert pf.next_charge_pull_applied is True
    assert pf.next_payment_at == next_payment - NEXT_CHARGE_PULL_FORWARD


@pytest.mark.django_db
def test_apply_early_pulls_subscription_next_payment_within_12h_window(bc):
    utc = timezone.now()
    future = utc + relativedelta(months=1)
    model = bc.database.create(
        country=1,
        city=1,
        academy=1,
        user=1,
        provisioning_vendor=1,
        subscription={
            "valid_until": future,
            "next_payment_at": future,
            "seat_service_item_id": None,
            "next_charge_pull_applied": False,
        },
        service={"type": "VOID"},
        service_item={"service_id": 1, "how_many": 1, "third_party_billing_cycle": True},
        subscription_service_item={"subscription_id": 1, "service_item_id": 1},
    )
    si = model.service_item
    sub = model.subscription
    c = Consumable.objects.create(
        user=model.user,
        service_item=si,
        unit_type=UNIT,
        how_many=1,
        subscription=sub,
        valid_until=future,
    )
    created_at = utc - timedelta(hours=4)
    provisioned_at = created_at + timedelta(hours=2)

    vps = ProvisioningVPS.objects.create(
        user=model.user,
        academy=model.academy,
        vendor=model.provisioning_vendor,
        consumed_consumable=c,
        status=ProvisioningVPS.VPS_STATUS_ACTIVE,
        provisioned_at=provisioned_at,
    )

    with _patch_reschedule(), _patch_consumable_lookup_for_vps(vps, created_at=created_at):
        apply_early_vps_billing_alignment(vps)

    sub.refresh_from_db()
    assert sub.next_charge_pull_applied is True
    assert sub.next_payment_at == future - NEXT_CHARGE_PULL_FORWARD


@pytest.mark.django_db
def test_apply_early_skips_when_provisioned_after_12h_from_consumable_creation(bc):
    utc = timezone.now()
    future = utc + relativedelta(months=1)
    model = bc.database.create(
        country=1,
        city=1,
        academy=1,
        user=1,
        provisioning_vendor=1,
        subscription={
            "valid_until": future,
            "next_payment_at": future,
            "seat_service_item_id": None,
            "next_charge_pull_applied": False,
        },
        service={"type": "VOID"},
        service_item={"service_id": 1, "how_many": 1, "third_party_billing_cycle": True},
        subscription_service_item={"subscription_id": 1, "service_item_id": 1},
    )
    si = model.service_item
    sub = model.subscription
    c = Consumable.objects.create(
        user=model.user,
        service_item=si,
        unit_type=UNIT,
        how_many=1,
        subscription=sub,
        valid_until=future,
    )
    created_at = utc - timedelta(hours=20)
    provisioned_at = created_at + EARLY_USE_AFTER_CONSUMABLE_CREATION + timedelta(hours=1)

    vps = ProvisioningVPS.objects.create(
        user=model.user,
        academy=model.academy,
        vendor=model.provisioning_vendor,
        consumed_consumable=c,
        status=ProvisioningVPS.VPS_STATUS_ACTIVE,
        provisioned_at=provisioned_at,
    )

    with _patch_reschedule() as mock_reschedule, _patch_consumable_lookup_for_vps(vps, created_at=created_at):
        apply_early_vps_billing_alignment(vps)

    sub.refresh_from_db()
    assert sub.next_charge_pull_applied is False
    assert sub.next_payment_at == future
    mock_reschedule.assert_not_called()


@pytest.mark.django_db
def test_apply_early_skips_without_third_party_billing_cycle(bc):
    utc = timezone.now()
    future = utc + relativedelta(months=1)
    model = bc.database.create(
        country=1,
        city=1,
        academy=1,
        user=1,
        provisioning_vendor=1,
        subscription={
            "valid_until": future,
            "next_payment_at": future,
            "seat_service_item_id": None,
            "next_charge_pull_applied": False,
        },
        service={"type": "VOID"},
        service_item={"service_id": 1, "how_many": 1, "third_party_billing_cycle": False},
        subscription_service_item={"subscription_id": 1, "service_item_id": 1},
    )
    si = model.service_item
    sub = model.subscription
    c = Consumable.objects.create(
        user=model.user,
        service_item=si,
        unit_type=UNIT,
        how_many=1,
        subscription=sub,
        valid_until=future,
    )
    created_at = utc - timedelta(hours=1)
    provisioned_at = created_at + timedelta(minutes=30)

    vps = ProvisioningVPS.objects.create(
        user=model.user,
        academy=model.academy,
        vendor=model.provisioning_vendor,
        consumed_consumable=c,
        status=ProvisioningVPS.VPS_STATUS_ACTIVE,
        provisioned_at=provisioned_at,
    )

    stub = SimpleNamespace(
        id=c.id,
        created_at=created_at,
        subscription_id=c.subscription_id,
        plan_financing_id=c.plan_financing_id,
        service_item_id=c.service_item_id,
        service_item=SimpleNamespace(third_party_billing_cycle=False),
    )
    qs = MagicMock()
    qs.select_related.return_value = qs
    qs.only.return_value = qs
    qs.first.return_value = stub

    with _patch_reschedule() as mock_reschedule, patch("breathecode.provisioning.actions.Consumable.objects.filter", return_value=qs):
        apply_early_vps_billing_alignment(vps)

    sub.refresh_from_db()
    assert sub.next_charge_pull_applied is False
    assert sub.next_payment_at == future
    mock_reschedule.assert_not_called()


@pytest.mark.django_db
def test_apply_early_subscription_pull_at_most_once(bc):
    utc = timezone.now()
    future = utc + relativedelta(months=1)
    model = bc.database.create(
        country=1,
        city=1,
        academy=1,
        user=1,
        provisioning_vendor=1,
        subscription={
            "valid_until": future,
            "next_payment_at": future,
            "seat_service_item_id": None,
            "next_charge_pull_applied": False,
        },
        service={"type": "VOID"},
        service_item={"service_id": 1, "how_many": 1, "third_party_billing_cycle": True},
        subscription_service_item={"subscription_id": 1, "service_item_id": 1},
    )
    si = model.service_item
    sub = model.subscription

    def make_vps(provisioned_at):
        c = Consumable.objects.create(
            user=model.user,
            service_item=si,
            unit_type=UNIT,
            how_many=1,
            subscription=sub,
            valid_until=future,
        )
        created_at = utc - timedelta(hours=2)
        vps = ProvisioningVPS.objects.create(
            user=model.user,
            academy=model.academy,
            vendor=model.provisioning_vendor,
            consumed_consumable=c,
            status=ProvisioningVPS.VPS_STATUS_ACTIVE,
            provisioned_at=provisioned_at,
        )
        return vps, created_at

    vps1, ca1 = make_vps(utc - timedelta(hours=1))
    vps2, ca2 = make_vps(utc - timedelta(minutes=30))

    def consumable_stub(c, created_at):
        return SimpleNamespace(
            id=c.id,
            created_at=created_at,
            subscription_id=c.subscription_id,
            plan_financing_id=c.plan_financing_id,
            service_item_id=c.service_item_id,
            service_item=c.service_item,
        )

    stubs = {
        vps1.consumed_consumable_id: consumable_stub(vps1.consumed_consumable, ca1),
        vps2.consumed_consumable_id: consumable_stub(vps2.consumed_consumable, ca2),
    }

    def filter_side_effect(*args, **kwargs):
        pk = kwargs.get("id") or kwargs.get("pk")
        qs = MagicMock()
        qs.select_related.return_value = qs
        qs.only.return_value = qs
        qs.first.return_value = stubs[pk]
        return qs

    with _patch_reschedule() as mock_reschedule, patch(
        "breathecode.provisioning.actions.Consumable.objects.filter",
        side_effect=filter_side_effect,
    ):
        apply_early_vps_billing_alignment(vps1)
        apply_early_vps_billing_alignment(vps2)

    sub.refresh_from_db()
    assert sub.next_payment_at == future - NEXT_CHARGE_PULL_FORWARD
    assert mock_reschedule.call_count == 1


@pytest.mark.django_db
def test_apply_early_uses_vps_requested_at_when_consumable_has_no_created_at(bc):
    utc = timezone.now()
    future = utc + relativedelta(months=1)
    model = bc.database.create(
        country=1,
        city=1,
        academy=1,
        user=1,
        provisioning_vendor=1,
        subscription={
            "valid_until": future,
            "next_payment_at": future,
            "seat_service_item_id": None,
            "next_charge_pull_applied": False,
        },
        service={"type": "VOID"},
        service_item={"service_id": 1, "how_many": 1, "third_party_billing_cycle": True},
        subscription_service_item={"subscription_id": 1, "service_item_id": 1},
    )
    si = model.service_item
    sub = model.subscription
    c = Consumable.objects.create(
        user=model.user,
        service_item=si,
        unit_type=UNIT,
        how_many=1,
        subscription=sub,
        valid_until=future,
    )

    requested_at = utc - timedelta(hours=3)
    provisioned_at = requested_at + timedelta(hours=1)
    vps = ProvisioningVPS.objects.create(
        user=model.user,
        academy=model.academy,
        vendor=model.provisioning_vendor,
        consumed_consumable=c,
        status=ProvisioningVPS.VPS_STATUS_ACTIVE,
        requested_at=requested_at,
        provisioned_at=provisioned_at,
    )

    with _patch_reschedule():
        apply_early_vps_billing_alignment(vps)

    sub.refresh_from_db()
    assert sub.next_charge_pull_applied is True
    assert sub.next_payment_at == future - NEXT_CHARGE_PULL_FORWARD
