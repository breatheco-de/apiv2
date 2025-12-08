"""
Tests for AcademyNotifySettings model.
"""
from django.test import TestCase
from rest_framework.exceptions import ValidationError

from breathecode.admissions.models import Academy
from breathecode.notify.models import AcademyNotifySettings
from breathecode.tests.mixins import BreathecodeMixin


class AcademyNotifySettingsTestCase(TestCase, BreathecodeMixin):
    """Test AcademyNotifySettings model behavior."""

    def setUp(self):
        """Set up test case."""
        self.bc = self

        # Generate academy for testing
        self.bc.database.create(academy=1)
        self.academy = Academy.objects.first()

    def test_create_settings(self):
        """Test creating academy notification settings."""
        settings = AcademyNotifySettings.objects.create(
            academy=self.academy, template_variables={"global.COMPANY_NAME": "Test Academy"}
        )

        assert settings.academy == self.academy
        assert settings.template_variables == {"global.COMPANY_NAME": "Test Academy"}
        assert settings.id is not None

    def test_get_variable_override_template_specific(self):
        """Test getting template-specific variable override."""
        settings = AcademyNotifySettings.objects.create(
            academy=self.academy,
            template_variables={"template.welcome_academy.subject": "Custom Welcome", "global.COMPANY_NAME": "Test"},
        )

        result = settings.get_variable_override("welcome_academy", "subject")
        assert result == "Custom Welcome"

    def test_get_variable_override_global(self):
        """Test getting global variable override."""
        settings = AcademyNotifySettings.objects.create(
            academy=self.academy, template_variables={"global.COMPANY_NAME": "Test Academy"}
        )

        result = settings.get_variable_override("any_template", "COMPANY_NAME")
        assert result == "Test Academy"

    def test_get_variable_override_priority(self):
        """Test that template-specific overrides take priority over global."""
        settings = AcademyNotifySettings.objects.create(
            academy=self.academy,
            template_variables={
                "template.welcome_academy.COMPANY_NAME": "Template Specific",
                "global.COMPANY_NAME": "Global Value",
            },
        )

        result = settings.get_variable_override("welcome_academy", "COMPANY_NAME")
        assert result == "Template Specific"

    def test_get_all_overrides_for_template(self):
        """Test getting all overrides for a template."""
        settings = AcademyNotifySettings.objects.create(
            academy=self.academy,
            template_variables={
                "template.welcome_academy.subject": "Welcome!",
                "template.welcome_academy.MESSAGE": "Hello there",
                "global.COMPANY_NAME": "Test Academy",
                "template.other_template.subject": "Other",
            },
        )

        overrides = settings.get_all_overrides_for_template("welcome_academy")

        assert overrides["subject"] == "Welcome!"
        assert overrides["MESSAGE"] == "Hello there"
        assert overrides["COMPANY_NAME"] == "Test Academy"
        assert "Other" not in str(overrides)

    def test_variable_interpolation_simple(self):
        """Test simple variable interpolation."""
        settings = AcademyNotifySettings.objects.create(
            academy=self.academy,
            template_variables={
                "template.welcome_academy.subject": "Welcome to {{global.COMPANY_NAME}}!",
                "global.COMPANY_NAME": "Test Academy",
            },
        )

        overrides = settings.get_all_overrides_for_template("welcome_academy")

        assert overrides["subject"] == "Welcome to Test Academy!"
        assert overrides["COMPANY_NAME"] == "Test Academy"

    def test_variable_interpolation_nested(self):
        """Test nested variable interpolation."""
        settings = AcademyNotifySettings.objects.create(
            academy=self.academy,
            template_variables={
                "template.welcome_academy.subject": "{{global.greeting}}",
                "global.greeting": "Welcome to {{global.COMPANY_NAME}}",
                "global.COMPANY_NAME": "Test",
            },
        )

        overrides = settings.get_all_overrides_for_template("welcome_academy")

        assert overrides["subject"] == "Welcome to Test"

    def test_variable_interpolation_circular_protection(self):
        """Test protection against circular references."""
        settings = AcademyNotifySettings.objects.create(
            academy=self.academy,
            template_variables={"global.a": "{{global.b}}", "global.b": "{{global.a}}"},
        )

        # Should not raise, just stop at max depth
        overrides = settings.get_all_overrides_for_template("any_template")

        # After max_depth iterations, should still have template syntax
        assert "{{" in overrides["a"] or "{{" in overrides["b"]

    def test_validation_invalid_template_slug(self):
        """Test validation fails for invalid template slug."""
        settings = AcademyNotifySettings(
            academy=self.academy, template_variables={"template.invalid_slug.subject": "Test"}
        )

        with self.assertRaises(ValidationError) as context:
            settings.clean()

        assert "invalid_slug" in str(context.exception).lower()
        assert "not found" in str(context.exception).lower()

    def test_validation_invalid_variable_name(self):
        """Test validation fails for invalid variable name."""
        settings = AcademyNotifySettings(
            academy=self.academy, template_variables={"template.welcome_academy.INVALID_VAR": "Test"}
        )

        with self.assertRaises(ValidationError) as context:
            settings.clean()

        assert "INVALID_VAR" in str(context.exception)
        assert "not found" in str(context.exception).lower()

    def test_validation_invalid_key_format(self):
        """Test validation fails for invalid key format."""
        settings = AcademyNotifySettings(academy=self.academy, template_variables={"invalid_format": "Test"})

        with self.assertRaises(ValidationError) as context:
            settings.clean()

        assert "invalid" in str(context.exception).lower()

    def test_validation_global_variable_valid(self):
        """Test validation passes for global variables."""
        settings = AcademyNotifySettings(
            academy=self.academy, template_variables={"global.CUSTOM_VAR": "Test Value"}
        )

        # Should not raise
        settings.clean()

    def test_str_method(self):
        """Test __str__ method."""
        settings = AcademyNotifySettings.objects.create(academy=self.academy)

        assert str(settings) == f"Notification settings for {self.academy.name}"

    def test_disabled_templates_empty(self):
        """Test is_template_enabled with no disabled templates."""
        settings = AcademyNotifySettings.objects.create(academy=self.academy, disabled_templates=[])

        assert settings.is_template_enabled("welcome_academy") is True
        assert settings.is_template_enabled("any_template") is True

    def test_disabled_templates_specific(self):
        """Test is_template_enabled with disabled templates."""
        settings = AcademyNotifySettings.objects.create(
            academy=self.academy, disabled_templates=["welcome_academy", "nps_survey"]
        )

        assert settings.is_template_enabled("welcome_academy") is False
        assert settings.is_template_enabled("nps_survey") is False
        assert settings.is_template_enabled("verify_email") is True

    def test_validation_disabled_invalid_template(self):
        """Test validation fails for invalid template in disabled_templates."""
        settings = AcademyNotifySettings(academy=self.academy, disabled_templates=["invalid_template_slug"])

        with self.assertRaises(ValidationError) as context:
            settings.clean()

        assert "invalid_template_slug" in str(context.exception).lower()
        assert "not found" in str(context.exception).lower()

    def test_validation_disabled_not_list(self):
        """Test validation fails if disabled_templates is not a list."""
        settings = AcademyNotifySettings(academy=self.academy, disabled_templates="not_a_list")

        with self.assertRaises(ValidationError) as context:
            settings.clean()

        assert "must be a list" in str(context.exception).lower()

    def test_validation_disabled_non_string_item(self):
        """Test validation fails for non-string items in disabled_templates."""
        settings = AcademyNotifySettings(academy=self.academy, disabled_templates=[123, {"invalid": "object"}])

        with self.assertRaises(ValidationError) as context:
            settings.clean()

        assert "must be a string" in str(context.exception).lower()

