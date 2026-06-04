"""Tests for deprovision_service_receiver academy guard with standalone consumables."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from dateutil.relativedelta import relativedelta
from django.utils import timezone

from breathecode.payments.models import UNIT, Consumable, Service
from breathecode.provisioning.receivers import deprovision_service_receiver


@pytest.mark.django_db
@patch("breathecode.provisioning.receivers.get_service_deprovisioner")
def test_academy_deprovision_skips_when_other_standalone_entitlement(mock_get_deprovisioner, bc):
    utc = timezone.now()
    future = utc + relativedelta(months=1)
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
    expiring = Consumable.objects.create(
        user=model.user,
        service_item=model.service_item,
        unit_type=UNIT,
        how_many=1,
        standalone_invoice=model.invoice,
        valid_until=future,
    )
    model_other = bc.database.create(
        user=1,
        bag={"academy_id": 1, "user_id": 1},
        invoice={"bag_id": 2, "user_id": 1, "academy_id": 1},
    )
    Consumable.objects.create(
        user=model.user,
        service_item=model.service_item,
        unit_type=UNIT,
        how_many=1,
        standalone_invoice=model_other.invoice,
        valid_until=future + relativedelta(months=1),
    )

    deprovision_service_receiver(
        sender=Service,
        instance=model.service,
        user_id=model.user.id,
        context={"academy_id": model.academy.id},
    )

    mock_get_deprovisioner.assert_not_called()


@pytest.mark.django_db
@patch("breathecode.provisioning.receivers.get_service_deprovisioner")
def test_academy_deprovision_proceeds_when_expiring_consumable_no_longer_active(mock_get_deprovisioner, bc):
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
    expiring = Consumable.objects.create(
        user=model.user,
        service_item=model.service_item,
        unit_type=UNIT,
        how_many=1,
        standalone_invoice=model.invoice,
        valid_until=utc - relativedelta(minutes=5),
    )
    mock_deprovisioner = MagicMock()
    mock_get_deprovisioner.return_value = mock_deprovisioner

    deprovision_service_receiver(
        sender=Service,
        instance=model.service,
        user_id=model.user.id,
        context={"academy_id": model.academy.id},
    )

    mock_get_deprovisioner.assert_called_once_with("free-monthly-llm-budget")
    mock_deprovisioner.assert_called_once()
