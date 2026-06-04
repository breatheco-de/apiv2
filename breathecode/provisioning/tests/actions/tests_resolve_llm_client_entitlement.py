"""Tests for LLM key entitlement checks (including standalone grants)."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from dateutil.relativedelta import relativedelta
from django.utils import timezone

from breathecode.payments.models import UNIT, Consumable
from breathecode.provisioning.actions import resolve_llm_client_and_external_id

from ..mixins import ProvisioningTestCase


class ResolveLLMClientEntitlementTestSuite(ProvisioningTestCase):
    @pytest.mark.django_db
    @patch("breathecode.provisioning.actions.ensure_llm_user")
    @patch("breathecode.provisioning.actions.get_llm_client")
    @patch("breathecode.provisioning.actions.resolve_provisioning_academy_for_llm")
    def test_resolve_llm_client_accepts_standalone_grant_consumable(
        self,
        resolve_pa_mock,
        get_llm_client_mock,
        ensure_llm_user_mock,
    ):
        utc_now = timezone.now()
        model = self.bc.database.create(
            country=1,
            city=1,
            academy=1,
            user=1,
            profile_academy=1,
            provisioning_vendor=1,
            provisioning_academy=1,
            service={
                "type": "VOID",
                "slug": "free-monthly-llm-budget",
                "consumer": "MONTHLY_LLM_BUDGET",
            },
            service_item={"service_id": 1, "how_many": 1},
            bag={"academy_id": 1, "user_id": 1},
            invoice={"bag_id": 1, "user_id": 1, "academy_id": 1},
        )
        model.provisioning_vendor.name = "litellm"
        model.provisioning_vendor.save()
        model.provisioning_academy.credentials_token = "token"
        model.provisioning_academy.save()

        Consumable.objects.create(
            user=model.user,
            service_item=model.service_item,
            unit_type=UNIT,
            how_many=1,
            standalone_invoice=model.invoice,
            valid_until=utc_now + relativedelta(months=1),
        )

        resolve_pa_mock.return_value = model.provisioning_academy
        get_llm_client_mock.return_value = MagicMock()
        ensure_llm_user_mock.return_value = MagicMock(external_user_id=f"{model.user.username}-{model.academy.slug}")

        request = MagicMock()
        request.user = model.user
        request.headers = {"Academy": str(model.academy.id)}

        client, external_user_id = resolve_llm_client_and_external_id(request, ensure_llm_user_record=True)

        assert client is get_llm_client_mock.return_value
        assert external_user_id == f"{model.user.username}-{model.academy.slug}"
