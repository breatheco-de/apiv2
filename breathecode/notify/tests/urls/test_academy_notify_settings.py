"""
Tests for AcademyNotifySettings API endpoints.
"""
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from breathecode.tests.mixins import BreathecodeMixin


class AcademyNotifySettingsViewTestCase(APITestCase, BreathecodeMixin):
    """Test AcademyNotifySettings API endpoints."""

    def setUp(self):
        """Set up test case."""
        self.bc = self

        # Generate user, academy, and role
        model = self.bc.database.create(user=1, role=1, capability="read_notification", academy=1)
        self.user = model.user
        self.academy = model.academy
        self.client.force_authenticate(user=self.user)

    def test_get_settings_without_auth(self):
        """Test GET endpoint without authentication."""
        self.client.force_authenticate(user=None)
        url = reverse("notify:academy_notify_settings")

        response = self.client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_settings_without_capability(self):
        """Test GET endpoint without read_notification capability."""
        # Create user without capability
        model = self.bc.database.create(user=1, academy=1)
        self.client.force_authenticate(user=model.user)
        url = reverse("notify:academy_notify_settings")

        response = self.client.get(url, headers={"Academy": str(self.academy.id)})

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_settings_nonexistent(self):
        """Test GET endpoint when settings don't exist."""
        url = reverse("notify:academy_notify_settings")

        response = self.client.get(url, headers={"Academy": str(self.academy.id)})

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"template_variables": {}, "academy": self.academy.id}

    def test_get_settings_existing(self):
        """Test GET endpoint with existing settings."""
        model = self.bc.database.create(
            academy_notify_settings=1,
            academy=self.academy,
            template_variables={"global.COMPANY_NAME": "Test Academy"},
        )

        url = reverse("notify:academy_notify_settings")

        response = self.client.get(url, headers={"Academy": str(self.academy.id)})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["template_variables"] == {"global.COMPANY_NAME": "Test Academy"}
        assert data["academy"] == self.academy.id

    def test_put_settings_without_auth(self):
        """Test PUT endpoint without authentication."""
        self.client.force_authenticate(user=None)
        url = reverse("notify:academy_notify_settings")

        response = self.client.put(url, {"template_variables": {}})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_put_settings_without_capability(self):
        """Test PUT endpoint without crud_notification capability."""
        # User has read but not crud capability
        url = reverse("notify:academy_notify_settings")

        response = self.client.put(
            url, {"template_variables": {"global.TEST": "value"}}, headers={"Academy": str(self.academy.id)}
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_put_settings_create(self):
        """Test PUT endpoint creates new settings."""
        # Give user crud capability
        model = self.bc.database.create(
            user=self.user, role=1, capability="crud_notification", academy=self.academy
        )

        url = reverse("notify:academy_notify_settings")

        response = self.client.put(
            url,
            {"template_variables": {"global.COMPANY_NAME": "New Academy"}},
            format="json",
            headers={"Academy": str(self.academy.id)},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["template_variables"] == {"global.COMPANY_NAME": "New Academy"}

    def test_put_settings_update(self):
        """Test PUT endpoint updates existing settings."""
        # Create existing settings
        model = self.bc.database.create(
            academy_notify_settings=1,
            academy=self.academy,
            template_variables={"global.OLD": "value"},
        )

        # Give user crud capability
        self.bc.database.create(user=self.user, role=1, capability="crud_notification", academy=self.academy)

        url = reverse("notify:academy_notify_settings")

        response = self.client.put(
            url,
            {"template_variables": {"global.COMPANY_NAME": "Updated"}},
            format="json",
            headers={"Academy": str(self.academy.id)},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["template_variables"] == {"global.COMPANY_NAME": "Updated"}

    def test_put_settings_validation_error(self):
        """Test PUT endpoint with invalid template slug."""
        # Give user crud capability
        self.bc.database.create(user=self.user, role=1, capability="crud_notification", academy=self.academy)

        url = reverse("notify:academy_notify_settings")

        response = self.client.put(
            url,
            {"template_variables": {"template.invalid_slug.subject": "Test"}},
            format="json",
            headers={"Academy": str(self.academy.id)},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "invalid_slug" in str(response.json()).lower()

    def test_put_settings_invalid_variable(self):
        """Test PUT endpoint with invalid variable name."""
        # Give user crud capability
        self.bc.database.create(user=self.user, role=1, capability="crud_notification", academy=self.academy)

        url = reverse("notify:academy_notify_settings")

        response = self.client.put(
            url,
            {"template_variables": {"template.welcome_academy.INVALID_VAR": "Test"}},
            format="json",
            headers={"Academy": str(self.academy.id)},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "INVALID_VAR" in str(response.json())

    def test_put_settings_with_disabled_templates(self):
        """Test PUT endpoint with disabled_templates."""
        # Give user crud capability
        self.bc.database.create(user=self.user, role=1, capability="crud_notification", academy=self.academy)

        url = reverse("notify:academy_notify_settings")

        response = self.client.put(
            url,
            {"disabled_templates": ["nps_survey", "welcome_academy"]},
            format="json",
            headers={"Academy": str(self.academy.id)},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "nps_survey" in data["disabled_templates"]
        assert "welcome_academy" in data["disabled_templates"]

    def test_put_settings_disabled_invalid_template(self):
        """Test PUT endpoint with invalid template in disabled_templates."""
        # Give user crud capability
        self.bc.database.create(user=self.user, role=1, capability="crud_notification", academy=self.academy)

        url = reverse("notify:academy_notify_settings")

        response = self.client.put(
            url,
            {"disabled_templates": ["invalid_template_slug"]},
            format="json",
            headers={"Academy": str(self.academy.id)},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "invalid_template_slug" in str(response.json()).lower()

