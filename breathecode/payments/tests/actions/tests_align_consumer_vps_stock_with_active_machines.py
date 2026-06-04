"""
Tests for align_consumer_vps_stock_with_active_machines (VPS pool scoped by billing context).

Ver trazas en consola (recomendado por pytest: *live logs*; no hace falta ``-s`` salvo que uses ``print()``):

  poetry run python -m pytest breathecode/payments/tests/actions/tests_align_consumer_vps_stock_with_active_machines.py --tb=short --log-cli-level=INFO

Detalle extra (IDs, kwargs de mocks, etc.):

  ... --log-cli-level=DEBUG

No usamos ``logging.getLogger(__name__)`` porque el logger ``breathecode`` tiene
``propagate: False`` en ``settings.py``: los mensajes no suben al *root* donde pytest
engancha el *live log*. Este módulo usa un logger de nombre plano bajo ``tests.…`` que sí
propaga.

Para fijarlo en el repo, se puede añadir en pytest.ini (afecta a toda la suite):

  [pytest]
  log_cli = true
  log_cli_level = INFO

Las migraciones y otros loggers pueden ser ruidosos en DEBUG; para centrarte en estas trazas filtra por
``tests.vps_align_consumer_vps_stock_with_active_machines``.
"""

from __future__ import annotations

import logging
from unittest.mock import patch

import pytest
from dateutil.relativedelta import relativedelta
from django.utils import timezone

from breathecode.payments import actions
from breathecode.payments.models import UNIT, Consumable, Service
from breathecode.provisioning.models import ProvisioningVPS

logger = logging.getLogger("tests.vps_align_consumer_vps_stock_with_active_machines")


@pytest.mark.django_db
def test_align_vps_only_deprovisions_machines_tied_to_same_subscription_pool(bc):
    """
    User has two subscriptions with VPS consumer credits. Subscription A has more ACTIVE
    machines than positive credits in A's pool; subscription B also has ACTIVE machines.

    Deprovision targets must only include VPS whose consumed_consumable belongs to
    subscription A — never B's machines (regression for multi-plan global deprovision).
    """
    logger.info("start test_align_vps_only_deprovisions_machines_tied_to_same_subscription_pool")
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
        service_item={"service_id": 1, "how_many": 5},
        subscription_service_item={"subscription_id": 1, "service_item_id": 1},
    )
    service = Service.objects.get(pk=1)
    service.consumer = Service.Consumer.VPS_SERVER
    service.save(update_fields=["consumer"])
    logger.debug("service id=%s slug=%r consumer=%s", service.id, service.slug, service.consumer)

    user = model_a.user
    academy = model_a.academy
    vendor = model_a.provisioning_vendor
    service_item_a = model_a.service_item

    model_b = bc.database.create(
        user=1,
        academy=1,
        subscription={
            "valid_until": future,
            "next_payment_at": future,
            "seat_service_item_id": None,
        },
        plan={"is_renewable": False},
        service_item={"service_id": 1, "how_many": 3},
        subscription_service_item={"subscription_id": 2, "service_item_id": 2},
    )
    sub_a = model_a.subscription
    sub_b = model_b.subscription
    service_item_b = model_b.service_item
    logger.debug("subscriptions A id=%s B id=%s user_id=%s", sub_a.id, sub_b.id, user.id)

    consumables_a = []
    for _ in range(3):
        consumables_a.append(
            Consumable.objects.create(
                user=user,
                service_item=service_item_a,
                unit_type=UNIT,
                how_many=0,
                subscription=sub_a,
                valid_until=future,
            )
        )

    consumables_b = []
    for _ in range(2):
        consumables_b.append(
            Consumable.objects.create(
                user=user,
                service_item=service_item_b,
                unit_type=UNIT,
                how_many=0,
                subscription=sub_b,
                valid_until=future,
            )
        )

    vps_a_ids = []
    for idx, c in enumerate(consumables_a):
        v = ProvisioningVPS.objects.create(
            user=user,
            academy=academy,
            vendor=vendor,
            consumed_consumable=c,
            status=ProvisioningVPS.VPS_STATUS_ACTIVE,
            provisioned_at=utc + relativedelta(seconds=idx),
        )
        vps_a_ids.append(v.id)

    vps_b_ids = []
    for idx, c in enumerate(consumables_b):
        v = ProvisioningVPS.objects.create(
            user=user,
            academy=academy,
            vendor=vendor,
            consumed_consumable=c,
            status=ProvisioningVPS.VPS_STATUS_ACTIVE,
            provisioned_at=utc + relativedelta(seconds=10 + idx),
        )
        vps_b_ids.append(v.id)

    logger.debug("VPS pool A ids=%s pool B ids=%s", vps_a_ids, vps_b_ids)

    # Single positive row for subscription A: 3 ACTIVE machines in A pool but only 1 credit.
    c_renew = Consumable.objects.create(
        user=user,
        service_item=service_item_a,
        unit_type=UNIT,
        how_many=1,
        subscription=sub_a,
        valid_until=future,
    )
    logger.debug(
        "c_renew id=%s subscription_id=%s how_many=%s",
        c_renew.id,
        c_renew.subscription_id,
        c_renew.how_many,
    )

    with (
        patch("breathecode.payments.actions.deprovision_service") as mock_deprovision,
        patch("breathecode.payments.actions.consume_service") as mock_consume,
    ):
        actions.align_consumer_vps_stock_with_active_machines(c_renew)

    mock_deprovision.send_robust.assert_called_once()
    _args, kwargs = mock_deprovision.send_robust.call_args
    targeted = set(kwargs.get("context", {}).get("provisioning_vps_ids", []))
    logger.debug("deprovision_service.send_robust kwargs=%s", kwargs)
    logger.debug("consume_service.send_robust call_args=%s", mock_consume.send_robust.call_args)

    assert len(targeted) == 2
    assert targeted.issubset(set(vps_a_ids))
    assert not targeted & set(vps_b_ids)

    mock_consume.send_robust.assert_called_once()
    logger.info("OK: deprovision scoped to subscription A only (no B VPS ids)")


@pytest.mark.django_db
def test_align_vps_no_deprovision_when_credits_cover_machines_in_pool(bc):
    logger.info("start test_align_vps_no_deprovision_when_credits_cover_machines_in_pool")
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
        },
        plan={"is_renewable": False},
        service={"type": "VOID", "slug": "vps_server"},
        service_item={"service_id": 1, "how_many": 5},
        subscription_service_item={"subscription_id": 1, "service_item_id": 1},
    )
    Service.objects.filter(pk=1).update(consumer=Service.Consumer.VPS_SERVER)

    user = model.user
    academy = model.academy
    vendor = model.provisioning_vendor
    si = model.service_item
    sub = model.subscription
    c_old = Consumable.objects.create(
        user=user,
        service_item=si,
        unit_type=UNIT,
        how_many=0,
        subscription=sub,
        valid_until=future,
    )
    ProvisioningVPS.objects.create(
        user=user,
        academy=academy,
        vendor=vendor,
        consumed_consumable=c_old,
        status=ProvisioningVPS.VPS_STATUS_ACTIVE,
        provisioned_at=utc,
    )

    c_renew = Consumable.objects.create(
        user=user,
        service_item=si,
        unit_type=UNIT,
        how_many=5,
        subscription=sub,
        valid_until=future,
    )

    with (
        patch("breathecode.payments.actions.deprovision_service") as mock_deprovision,
        patch("breathecode.payments.actions.consume_service") as mock_consume,
    ):
        actions.align_consumer_vps_stock_with_active_machines(c_renew)

    mock_deprovision.send_robust.assert_not_called()
    mock_consume.send_robust.assert_called_once()
    logger.info("OK: no deprovision when credits cover machines in pool")
