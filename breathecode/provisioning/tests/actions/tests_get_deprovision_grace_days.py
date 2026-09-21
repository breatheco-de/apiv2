from __future__ import annotations

import os
from datetime import timedelta
from unittest.mock import patch

from django.utils import timezone

from breathecode.provisioning.actions import (
    POWER_OFF_GRACE_RATIO,
    get_deprovision_at,
    get_deprovision_grace_days,
    get_power_off_at,
    get_power_off_grace_days,
    get_remaining_teardown_grace_days,
)


class TestGetDeprovisionGraceDays:
    @patch.dict(os.environ, {"THIRD_PARTY_DEPROVISION_GRACE_DAYS": "21"})
    def test_reads_env(self):
        assert get_deprovision_grace_days() == 21

    @patch.dict(os.environ, {"THIRD_PARTY_DEPROVISION_GRACE_DAYS": "9"})
    def test_adds_env_days_to_plan_expiry(self):
        plan_expires_at = timezone.now()
        assert get_deprovision_at(plan_expires_at) == plan_expires_at + timedelta(days=9)

    def test_returns_none_without_plan_expiry(self):
        assert get_deprovision_at(None) is None

    @patch.dict(os.environ, {"THIRD_PARTY_DEPROVISION_GRACE_DAYS": "100"})
    def test_clamps_to_ninety(self):
        assert get_deprovision_grace_days() == 90

    @patch.dict(os.environ, {"THIRD_PARTY_DEPROVISION_GRACE_DAYS": "nope"})
    def test_invalid_env_uses_fifteen(self):
        assert get_deprovision_grace_days() == 15

    @patch.dict(os.environ, {"THIRD_PARTY_DEPROVISION_GRACE_DAYS": "15"})
    def test_power_off_is_eighty_percent_of_grace(self):
        plan_expires_at = timezone.now()
        assert get_power_off_at(plan_expires_at) == plan_expires_at + timedelta(days=12)
        assert get_power_off_grace_days() == 12
        assert get_remaining_teardown_grace_days() == 3
        assert POWER_OFF_GRACE_RATIO == 0.8
        assert get_power_off_grace_days() + get_remaining_teardown_grace_days() == 15

    def test_power_off_returns_none_without_plan_expiry(self):
        assert get_power_off_at(None) is None
