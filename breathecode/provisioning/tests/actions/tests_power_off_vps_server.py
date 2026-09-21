"""Guards for power_off_vps_server: billing scope + consumable of that same context."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from dateutil.relativedelta import relativedelta
from django.utils import timezone

from breathecode.payments.models import UNIT, Consumable
from breathecode.provisioning.actions import power_off_vps_server
from breathecode.provisioning.models import ProvisioningVPS


def _vps_setup(bc, *, service_slug="vps_server"):
    utc = timezone.now()
    future = utc + relativedelta(months=1)
    model = bc.database.create(
        country=1,
        city=1,
        academy=1,
        user=1,
        provisioning_vendor=1,
        provisioning_academy=1,
        plan_financing={
            "next_payment_at": future,
            "valid_until": utc + relativedelta(months=6),
            "plan_expires_at": utc + relativedelta(years=1),
            "monthly_price": 100,
            "status": "ACTIVE",
        },
        service={"type": "VOID", "slug": service_slug, "consumer": "VPS_SERVER"},
        service_item={"how_many": 1},
    )
    return model, utc, future


def _create_vps(*, user, academy, vendor, consumable, utc, external_id="droplet-1"):
    return ProvisioningVPS.objects.create(
        user=user,
        academy=academy,
        vendor=vendor,
        consumed_consumable=consumable,
        status=ProvisioningVPS.VPS_STATUS_ACTIVE,
        provisioned_at=utc,
        external_id=external_id,
    )


@pytest.mark.django_db
def test_skips_without_subscription_or_plan_financing_id(bc):
    model, utc, future = _vps_setup(bc)
    c = Consumable.objects.create(
        user=model.user,
        service_item=model.service_item,
        unit_type=UNIT,
        how_many=0,
        plan_financing=model.plan_financing,
        valid_until=future,
    )
    _create_vps(
        user=model.user,
        academy=model.academy,
        vendor=model.provisioning_vendor,
        consumable=c,
        utc=utc,
    )

    with patch("breathecode.provisioning.actions.get_vps_client") as mock_client:
        power_off_vps_server(user_id=model.user.id, context={"academy_id": model.academy.id})

    mock_client.assert_not_called()


@pytest.mark.django_db
def test_skips_when_same_plan_financing_still_has_vps_consumable(bc):
    model, utc, future = _vps_setup(bc)
    Consumable.objects.create(
        user=model.user,
        service_item=model.service_item,
        unit_type=UNIT,
        how_many=1,
        plan_financing=model.plan_financing,
        valid_until=future,
    )
    used = Consumable.objects.create(
        user=model.user,
        service_item=model.service_item,
        unit_type=UNIT,
        how_many=0,
        plan_financing=model.plan_financing,
        valid_until=future,
    )
    _create_vps(
        user=model.user,
        academy=model.academy,
        vendor=model.provisioning_vendor,
        consumable=used,
        utc=utc,
    )

    with patch("breathecode.provisioning.actions.get_vps_client") as mock_client:
        power_off_vps_server(
            user_id=model.user.id,
            context={
                "academy_id": model.academy.id,
                "plan_financing_id": model.plan_financing.id,
            },
        )

    mock_client.assert_not_called()


@pytest.mark.django_db
def test_other_plan_financing_consumable_does_not_protect_this_vps(bc):
    model, utc, future = _vps_setup(bc)
    used = Consumable.objects.create(
        user=model.user,
        service_item=model.service_item,
        unit_type=UNIT,
        how_many=0,
        plan_financing=model.plan_financing,
        valid_until=future,
    )
    vps_this = _create_vps(
        user=model.user,
        academy=model.academy,
        vendor=model.provisioning_vendor,
        consumable=used,
        utc=utc,
        external_id="droplet-this",
    )

    other = bc.database.create(
        user=1,
        academy=1,
        plan_financing={
            "next_payment_at": future,
            "valid_until": utc + relativedelta(months=6),
            "plan_expires_at": utc + relativedelta(years=1),
            "monthly_price": 100,
            "status": "ACTIVE",
        },
        service_item={"service_id": model.service.id, "how_many": 1},
    )
    other_c = Consumable.objects.create(
        user=model.user,
        service_item=other.service_item,
        unit_type=UNIT,
        how_many=1,
        plan_financing=other.plan_financing,
        valid_until=future,
    )
    _create_vps(
        user=model.user,
        academy=model.academy,
        vendor=model.provisioning_vendor,
        consumable=other_c,
        utc=utc,
        external_id="droplet-other",
    )

    power_off = MagicMock()
    client = MagicMock()
    client.power_off_vps = power_off

    with patch("breathecode.provisioning.actions.get_vps_client", return_value=client):
        power_off_vps_server(
            user_id=model.user.id,
            context={
                "academy_id": model.academy.id,
                "plan_financing_id": model.plan_financing.id,
            },
        )

    power_off.assert_called_once()
    assert power_off.call_args[0][1] == vps_this.external_id


@pytest.mark.django_db
def test_powers_off_only_vps_tied_to_plan_financing(bc):
    model, utc, future = _vps_setup(bc)
    used = Consumable.objects.create(
        user=model.user,
        service_item=model.service_item,
        unit_type=UNIT,
        how_many=0,
        plan_financing=model.plan_financing,
        valid_until=future,
    )
    vps_this = _create_vps(
        user=model.user,
        academy=model.academy,
        vendor=model.provisioning_vendor,
        consumable=used,
        utc=utc,
        external_id="droplet-this",
    )

    other = bc.database.create(
        user=1,
        academy=1,
        plan_financing={
            "next_payment_at": future,
            "valid_until": utc + relativedelta(months=6),
            "plan_expires_at": utc + relativedelta(years=1),
            "monthly_price": 100,
            "status": "ACTIVE",
        },
        service_item={"service_id": model.service.id, "how_many": 1},
    )
    other_used = Consumable.objects.create(
        user=model.user,
        service_item=other.service_item,
        unit_type=UNIT,
        how_many=0,
        plan_financing=other.plan_financing,
        valid_until=future,
    )
    _create_vps(
        user=model.user,
        academy=model.academy,
        vendor=model.provisioning_vendor,
        consumable=other_used,
        utc=utc,
        external_id="droplet-other",
    )

    power_off = MagicMock()
    client = MagicMock()
    client.power_off_vps = power_off

    with patch("breathecode.provisioning.actions.get_vps_client", return_value=client):
        power_off_vps_server(
            user_id=model.user.id,
            context={"plan_financing_id": model.plan_financing.id},
        )

    power_off.assert_called_once()
    assert power_off.call_args[0][1] == vps_this.external_id


@pytest.mark.django_db
def test_skips_when_same_subscription_still_has_vps_consumable(bc):
    utc = timezone.now()
    future = utc + relativedelta(months=1)
    model = bc.database.create(
        country=1,
        city=1,
        academy=1,
        user=1,
        provisioning_vendor=1,
        provisioning_academy=1,
        subscription={
            "valid_until": future,
            "next_payment_at": future,
            "seat_service_item_id": None,
        },
        plan={"is_renewable": False, "time_of_life": 12, "time_of_life_unit": "MONTH"},
        service={"type": "VOID", "slug": "vps_server", "consumer": "VPS_SERVER"},
        service_item={"how_many": 1},
        subscription_service_item=True,
    )
    Consumable.objects.create(
        user=model.user,
        service_item=model.service_item,
        unit_type=UNIT,
        how_many=1,
        subscription=model.subscription,
        valid_until=future,
    )
    used = Consumable.objects.create(
        user=model.user,
        service_item=model.service_item,
        unit_type=UNIT,
        how_many=0,
        subscription=model.subscription,
        valid_until=future,
    )
    _create_vps(
        user=model.user,
        academy=model.academy,
        vendor=model.provisioning_vendor,
        consumable=used,
        utc=utc,
    )

    with patch("breathecode.provisioning.actions.get_vps_client") as mock_client:
        power_off_vps_server(
            user_id=model.user.id,
            context={"subscription_id": model.subscription.id},
        )

    mock_client.assert_not_called()
