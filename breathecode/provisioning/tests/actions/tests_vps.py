"""Tests for VPS actions: get_eligible_academy_and_vendor_for_vps, request_vps."""

from unittest.mock import MagicMock, patch

import pytest
from capyc.rest_framework.exceptions import ValidationException

from breathecode.authenticate.models import ACTIVE as PROFILE_ACADEMY_ACTIVE

from breathecode.provisioning.actions import (
    get_eligible_academy_and_vendor_for_vps,
    request_vps,
    request_vps_for_student,
)
from breathecode.provisioning.models import ProvisioningVPS

from ..mixins import ProvisioningTestCase


@pytest.mark.django_db
class TestGetEligibleAcademyAndVendorForVps(ProvisioningTestCase):
    def test_no_academy_raises(self):
        model = self.bc.database.create(user=1)
        with pytest.raises(ValidationException) as exc_info:
            get_eligible_academy_and_vendor_for_vps(model.user)
        assert "no-academy-for-vps" in str(exc_info.value).lower() or "slug" in str(exc_info.value).lower()

    def test_academy_without_vps_config_raises(self):
        model = self.bc.database.create(user=1, profile_academy=1, academy=1)
        with pytest.raises(ValidationException):
            get_eligible_academy_and_vendor_for_vps(model.user)

    @patch("breathecode.provisioning.actions.get_vps_client")
    def test_returns_academy_and_provisioning_academy_when_configured(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        model = self.bc.database.create(user=1, profile_academy=1)
        academy = model.profile_academy.academy
        other = self.bc.database.create(
            academy=academy,
            provisioning_vendor={"name": "hostinger"},
            provisioning_profile={},
            provisioning_academy={"credentials_token": "tok"},
        )
        # Link profile to academy and vendor
        other.provisioning_profile.academy = academy
        other.provisioning_profile.vendor = other.provisioning_vendor
        other.provisioning_profile.save()
        other.provisioning_academy.academy = academy
        other.provisioning_academy.vendor = other.provisioning_vendor
        other.provisioning_academy.save()
        academy, prov_academy = get_eligible_academy_and_vendor_for_vps(model.user)
        assert academy is not None
        assert prov_academy is not None
        assert prov_academy.academy_id == academy.id


@pytest.mark.django_db
class TestRequestVps(ProvisioningTestCase):
    @patch("breathecode.provisioning.actions.get_vps_client")
    @patch("breathecode.provisioning.actions.get_eligible_academy_and_vendor_for_vps")
    def test_request_vps_rejects_when_no_consumables(self, mock_eligible, mock_client):
        model = self.bc.database.create(user=1, academy=1)
        mock_eligible.return_value = (model.academy, MagicMock())
        mock_eligible.return_value[1].vendor = MagicMock()
        with patch("breathecode.provisioning.actions.Consumable") as mock_consumable:
            qs = MagicMock()
            qs.filter.return_value = qs
            qs.exists.return_value = False
            mock_consumable.list.return_value = qs
            with pytest.raises(ValidationException) as exc_info:
                request_vps(model.user)
            assert "insufficient-vps-server-credits" in str(exc_info.value).lower() or "credits" in str(
                exc_info.value
            ).lower()


@pytest.mark.django_db
class TestRequestVpsForStudent(ProvisioningTestCase):
    def test_rejects_when_student_not_in_academy(self):
        m_staff_academy = self.bc.database.create(user=1, academy=1)
        m_student = self.bc.database.create(user=1)
        student = m_student.user
        academy = m_staff_academy.academy
        with pytest.raises(ValidationException) as exc_info:
            request_vps_for_student(student, academy, lang="en")
        assert "student-not-in-academy" in str(exc_info.value).lower()

    @patch("breathecode.provisioning.actions._request_vps_core")
    @patch("breathecode.provisioning.actions.get_vps_client")
    def test_delegates_to_core_when_student_is_member(self, mock_get_client, mock_core):
        mock_get_client.return_value = MagicMock()
        model = self.bc.database.create(
            user=1,
            profile_academy=1,
            academy=1,
            role=1,
        )
        student = model.user
        academy = model.academy
        pa = model.profile_academy
        pa.user = student
        pa.academy = academy
        pa.status = PROFILE_ACADEMY_ACTIVE
        pa.save()
        other = self.bc.database.create(
            academy=academy,
            provisioning_vendor={"name": "hostinger"},
            provisioning_profile={},
            provisioning_academy={"credentials_token": "tok"},
        )
        other.provisioning_profile.academy = academy
        other.provisioning_profile.vendor = other.provisioning_vendor
        other.provisioning_profile.save()
        other.provisioning_academy.academy = academy
        other.provisioning_academy.vendor = other.provisioning_vendor
        other.provisioning_academy.save()

        mock_vps = MagicMock()
        mock_vps.id = 42
        mock_core.return_value = mock_vps
        out = request_vps_for_student(student, academy, plan_slug="default", lang="en")
        assert out.id == 42
        mock_core.assert_called_once()
        _, call_kwargs = mock_core.call_args
        assert call_kwargs["lang"] == "en"
        assert call_kwargs["for_staff"] is True
