"""Tests for renew_or_deprovision_vps_task."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from breathecode.payments.models import UNIT, Consumable
from breathecode.provisioning.models import ProvisioningVPS
from breathecode.provisioning.tasks import renew_or_deprovision_vps_task


@pytest.mark.django_db
@patch("breathecode.provisioning.tasks.deprovision_vps_task")
def test_renew_updates_consumed_consumable_to_new_credit(mock_deprovision, bc):
    """When renewing with a new credit, VPS.consumed_consumable must point at that credit."""
    now = timezone.now()
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

    old_consumable = Consumable.objects.create(
        user=model.user,
        service_item=model.service_item,
        unit_type=UNIT,
        how_many=0,
        standalone_invoice=model.invoice,
        valid_until=now - timedelta(days=1),
    )
    new_consumable = Consumable.objects.create(
        user=model.user,
        service_item=model.service_item,
        unit_type=UNIT,
        how_many=1,
        standalone_invoice=model.invoice,
        valid_until=now + timedelta(days=30),
    )
    vps = ProvisioningVPS.objects.create(
        user=model.user,
        academy=model.academy,
        vendor=model.provisioning_vendor,
        consumed_consumable=old_consumable,
        status=ProvisioningVPS.VPS_STATUS_ACTIVE,
        external_id="582656258",
    )

    renew_or_deprovision_vps_task(vps.id)

    vps.refresh_from_db()
    new_consumable.refresh_from_db()
    old_consumable.refresh_from_db()

    assert vps.consumed_consumable_id == new_consumable.id
    assert new_consumable.how_many == 0
    assert old_consumable.how_many == 0
    mock_deprovision.assert_not_called()
