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

    def test_lang_specific_override_does_not_cross_language(self):
        """EN override must not apply when resolving for ES (falls back to no override)."""
        settings = AcademyNotifySettings.objects.create(
            academy=self.academy,
            template_variables={
                "template.verify_email.SUBJECT_EVENT.en": "EN only {CONTEXT_NAME}",
                "template.verify_email.MESSAGE_EVENT.en": "EN body",
            },
        )

        en_overrides = settings.get_all_overrides_for_template("verify_email", lang="en")
        es_overrides = settings.get_all_overrides_for_template("verify_email", lang="es")

        assert en_overrides["SUBJECT_EVENT"] == "EN only {CONTEXT_NAME}"
        assert en_overrides["MESSAGE_EVENT"] == "EN body"
        assert "SUBJECT_EVENT" not in es_overrides
        assert "MESSAGE_EVENT" not in es_overrides

    def test_lang_specific_es_override(self):
        settings = AcademyNotifySettings.objects.create(
            academy=self.academy,
            template_variables={
                "template.verify_email.SUBJECT_EVENT.es": "ES evento {CONTEXT_NAME}",
                "template.verify_email.SUBJECT_EVENT.en": "EN event {CONTEXT_NAME}",
            },
        )

        es_overrides = settings.get_all_overrides_for_template("verify_email", lang="es")
        en_overrides = settings.get_all_overrides_for_template("verify_email", lang="en-US")

        assert es_overrides["SUBJECT_EVENT"] == "ES evento {CONTEXT_NAME}"
        assert en_overrides["SUBJECT_EVENT"] == "EN event {CONTEXT_NAME}"

    def test_legacy_override_applies_to_all_langs(self):
        """Keys without lang suffix still apply for any lang."""
        settings = AcademyNotifySettings.objects.create(
            academy=self.academy,
            template_variables={"template.verify_email.subject": "Legacy subject"},
        )

        en_overrides = settings.get_all_overrides_for_template("verify_email", lang="en")
        es_overrides = settings.get_all_overrides_for_template("verify_email", lang="es")

        assert en_overrides["subject"] == "Legacy subject"
        assert es_overrides["subject"] == "Legacy subject"

    def test_lang_specific_wins_over_legacy(self):
        settings = AcademyNotifySettings.objects.create(
            academy=self.academy,
            template_variables={
                "template.verify_email.SUBJECT_EVENT": "Legacy all langs",
                "template.verify_email.SUBJECT_EVENT.es": "ES specific",
            },
        )

        es_overrides = settings.get_all_overrides_for_template("verify_email", lang="es")
        en_overrides = settings.get_all_overrides_for_template("verify_email", lang="en")

        assert es_overrides["SUBJECT_EVENT"] == "ES specific"
        assert en_overrides["SUBJECT_EVENT"] == "Legacy all langs"

    def test_validation_accepts_lang_suffix(self):
        settings = AcademyNotifySettings(
            academy=self.academy,
            template_variables={
                "template.verify_email.SUBJECT_EVENT.en": "Hello {CONTEXT_NAME}",
                "template.verify_email.MESSAGE_EVENT.es": "Hola {CONTEXT_NAME}",
            },
        )
        settings.clean()  # should not raise

    def test_validation_rejects_invalid_lang_code(self):
        settings = AcademyNotifySettings(
            academy=self.academy,
            template_variables={"template.verify_email.SUBJECT_EVENT.english": "Bad"},
        )

        with self.assertRaises(ValidationError) as context:
            settings.clean()

        assert "language" in str(context.exception).lower() or "english" in str(context.exception).lower()

    def test_get_variable_override_with_lang(self):
        settings = AcademyNotifySettings.objects.create(
            academy=self.academy,
            template_variables={
                "template.verify_email.SUBJECT_EVENT.en": "EN",
                "template.verify_email.SUBJECT_EVENT": "Legacy",
            },
        )

        assert settings.get_variable_override("verify_email", "SUBJECT_EVENT", lang="en") == "EN"
        assert settings.get_variable_override("verify_email", "SUBJECT_EVENT", lang="es") == "Legacy"
        assert settings.get_variable_override("verify_email", "SUBJECT_EVENT") == "Legacy"

