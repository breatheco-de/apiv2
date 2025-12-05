import re
import traceback
from collections import OrderedDict
from typing import Dict, Literal, Optional

from asgiref.sync import async_to_sync, sync_to_async
from channels.layers import get_channel_layer
from django import forms
from django.conf import settings
from django.contrib.auth.models import User
from django.core import serializers
from django.db import models
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from breathecode.admissions.models import Academy, Cohort

__all__ = [
    "UserProxy",
    "CohortProxy",
    "Device",
    "SlackTeam",
    "SlackUser",
    "SlackUserTeam",
    "SlackChannel",
    "Hook",
    "AcademyNotifySettings",
]
AUTH_USER_MODEL = getattr(settings, "AUTH_USER_MODEL", "auth.User")
if getattr(settings, "HOOK_CUSTOM_MODEL", None) is None:
    settings.HOOK_CUSTOM_MODEL = "notify.Hook"


class UserProxy(User):

    class Meta:
        proxy = True


class CohortProxy(Cohort):

    class Meta:
        proxy = True


class Device(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    registration_id = models.TextField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.user.registration_id


INCOMPLETED = "INCOMPLETED"
COMPLETED = "COMPLETED"
SYNC_STATUS = (
    (INCOMPLETED, "Incompleted"),
    (COMPLETED, "Completed"),
)


class SlackTeam(models.Model):

    slack_id = models.CharField(max_length=50)
    name = models.CharField(max_length=100)

    # the owner represents the channel
    # his/her credentials are used for interaction with the Slack API
    owner = models.ForeignKey(User, on_delete=models.CASCADE)

    academy = models.OneToOneField(Academy, on_delete=models.CASCADE, blank=True)

    sync_status = models.CharField(
        max_length=15, choices=SYNC_STATUS, default=INCOMPLETED, help_text="Automatically set when synqued from slack"
    )
    sync_message = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        default=None,
        help_text="Contains any success or error messages depending on the status",
    )
    synqued_at = models.DateTimeField(default=None, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f"{self.name} ({self.slack_id})"


class SlackUser(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, blank=True, null=True, default=None)

    slack_id = models.CharField(max_length=50)
    status_text = models.CharField(max_length=255, blank=True, null=True)
    status_emoji = models.CharField(max_length=100, blank=True, null=True)
    real_name = models.CharField(max_length=100, blank=True, null=True)
    display_name = models.CharField(max_length=100, blank=True, null=True)
    email = models.CharField(max_length=100, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.slack_id


class SlackUserTeam(models.Model):
    slack_user = models.ForeignKey(SlackUser, on_delete=models.CASCADE)
    slack_team = models.ForeignKey(SlackTeam, on_delete=models.CASCADE)

    sync_status = models.CharField(max_length=15, choices=SYNC_STATUS, default=INCOMPLETED)
    sync_message = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        default=None,
        help_text="Contains any success or error messages depending on the status",
    )
    synqued_at = models.DateTimeField(default=None, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)


class SlackChannel(models.Model):
    cohort = models.OneToOneField(Cohort, on_delete=models.CASCADE, blank=True, null=True, default=None)
    # academy = models.OneToOneField(Academy, on_delete=models.CASCADE, blank=True, null=True, default=None)

    slack_id = models.CharField(max_length=50)
    team = models.ForeignKey(SlackTeam, on_delete=models.CASCADE)
    name = models.CharField(max_length=100, blank=True, null=True)

    topic = models.CharField(max_length=500, blank=True, null=True)
    purpose = models.CharField(max_length=500, blank=True, null=True)

    sync_status = models.CharField(max_length=15, choices=SYNC_STATUS, default=INCOMPLETED)
    sync_message = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        default=None,
        help_text="Contains any success or error messages depending on the status",
    )
    synqued_at = models.DateTimeField(default=None, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        name = self.name if self.name else "Unknown"
        return f"{name}({self.slack_id})"


class AbstractHook(models.Model):
    """
    Stores a representation of a Hook.
    """

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    user = models.ForeignKey(AUTH_USER_MODEL, related_name="%(class)ss", on_delete=models.CASCADE)
    event = models.CharField("Event", max_length=64, db_index=True)
    target = models.URLField("Target URL", max_length=255)
    service_id = models.CharField("Service ID", max_length=64, null=True, default=None, blank=True)
    sample_data = models.JSONField(
        null=True, default=None, blank=True, help_text="Use this as an example on what you will be receiving"
    )

    total_calls = models.IntegerField(default=0)
    last_call_at = models.DateTimeField(null=True, blank=True, default=None)
    last_response_code = models.IntegerField(null=True, blank=True, default=None)

    class Meta:
        abstract = True

    def clean(self):
        from .utils.hook_manager import HookManager

        """ Validation for events. """
        if self.event not in HookManager.HOOK_EVENTS.keys():
            raise ValidationError("Invalid hook event {evt}.".format(evt=self.event))

    def dict(self):
        return {"id": self.id, "event": self.event, "target": self.target}

    def serialize_hook(self, instance):
        """
        Serialize the object down to Python primitives.
        By default it uses Django's built in serializer.
        """
        from .utils.hook_manager import HookManager

        if getattr(instance, "serialize_hook", None) and callable(instance.serialize_hook):
            return instance.serialize_hook(hook=self)
        if getattr(settings, "HOOK_SERIALIZER", None):
            serializer = HookManager.get_module(settings.HOOK_SERIALIZER)
            return serializer(instance, hook=self)
        # if no user defined serializers, fallback to the django builtin!
        data = serializers.serialize("python", [instance])[0]
        for k, v in data.items():
            if isinstance(v, OrderedDict):
                data[k] = dict(v)

        if isinstance(data, OrderedDict):
            data = dict(data)

        return {
            "hook": self.dict(),
            "data": data,
        }

    def __unicode__(self):
        return "{} => {}".format(self.event, self.target)


class Hook(AbstractHook):

    class Meta(AbstractHook.Meta):
        swappable = "HOOK_CUSTOM_MODEL"


class HookError(models.Model):
    """Hook Error."""

    message = models.CharField(max_length=255)
    event = models.CharField("Event", max_length=64, db_index=True)
    hooks = models.ManyToManyField(Hook, related_name="errors", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Notification(models.Model):
    """
    This model works like:
    1. a promise of delivery a notification to a user or academy.
    2. a stateless way to emit notifications to the frontend.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        DONE = "DONE", "Done"
        SENT = "SENT", "Sent"
        SEEN = "SEEN", "Seen"

    class Type(models.TextChoices):
        INFO = "INFO", "Info"
        WARNING = "WARNING", "Warning"
        ERROR = "ERROR", "Error"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._status = self.status

    operation_code = models.CharField(max_length=20)
    message = models.TextField(blank=True, null=True, default=None)

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, default=None)
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE, null=True, blank=True, default=None)
    meta = models.JSONField(blank=True, null=True, default=None)

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    type = models.CharField(max_length=10, choices=Type.choices, default=Type.INFO)
    done_at = models.DateTimeField(blank=True, null=True, default=None)
    sent_at = models.DateTimeField(blank=True, null=True, default=None)
    seen_at = models.DateTimeField(blank=True, null=True, default=None)

    def __str__(self):
        return self.operation_code

    def clean(self):
        if any([self.user, self.academy]) is False:
            raise forms.ValidationError("Either user or academy must be provided")

        if self.status == self.Status.DONE:
            self.done_at = timezone.now()

        if self.status == self.Status.PENDING:
            self.sent_at = None

        super().clean()

    @async_to_sync
    async def _send_notification(self):
        channel_layer = get_channel_layer()

        user_id = self.user.id if self.user else None
        academy_id = self.academy.id if self.academy else None

        await channel_layer.send(
            f"notification_{user_id}_{academy_id}",
            {
                "type": "notification.refresh",
                "user": user_id,
                "academy": academy_id,
            },
        )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

        if self.status != self._status and self.status == self.Status.DONE:
            try:
                self._send_notification()
            except Exception:
                traceback.print_exc()

        self._status = self.status

    @classmethod
    def send(cls, message: tuple[Literal["INFO", "WARNING", "ERROR"], str], notification: "Notification"):
        if notification.status == Notification.Status.PENDING:
            notification.message = message[1]
            notification.status = Notification.Status.DONE
            notification.type = message[0]
            notification.save()

    @classmethod
    @sync_to_async
    def asend(cls, message: tuple[Literal["INFO", "WARNING", "ERROR"], str], notification: "Notification"):
        cls.send(message, notification)

    @classmethod
    async def aemit(
        cls,
        message: tuple[Literal["INFO", "WARNING", "ERROR"], str],
        user: Optional[User] = None,
        academy: Optional[Academy] = None,
    ) -> None:
        """Emit a notification that won't be saved"""

        user_id = None
        academy_id = None

        if isinstance(user, User):
            user_id = user.id

        elif isinstance(user, int):
            user_id = user

        if isinstance(academy, Academy):
            academy_id = academy.id

        elif isinstance(academy, int):
            academy_id = academy

        channel_layer = get_channel_layer()

        await channel_layer.send(
            f"notification_{user_id}_{academy_id}",
            {
                "type": "notification.push",
                "user": user_id,
                "academy": academy_id,
                "level": message[0],
                "message": message[1],
            },
        )

    @classmethod
    @async_to_sync
    async def emit(
        cls,
        message: tuple[Literal["INFO", "WARNING", "ERROR"], str],
        user: Optional[User] = None,
        academy: Optional[Academy] = None,
    ) -> None:
        await cls.aemit(message, user, academy)

    @classmethod
    def info(cls, message: str) -> tuple[Literal["INFO", "WARNING", "ERROR"], str]:
        return ("INFO", message)

    @classmethod
    def warning(cls, message: str) -> tuple[Literal["INFO", "WARNING", "ERROR"], str]:
        return ("WARNING", message)

    @classmethod
    def error(cls, message: str) -> tuple[Literal["INFO", "WARNING", "ERROR"], str]:
        return ("ERROR", message)


class AcademyNotifySettings(models.Model):
    """
    Per-academy notification variable overrides.
    Allows academies to customize notification content without code changes.
    """

    academy = models.OneToOneField(Academy, on_delete=models.CASCADE, related_name="notify_settings")

    template_variables = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Variable overrides for notification templates.\n"
            "Format:\n"
            "  - Template-specific: 'template.SLUG.VARIABLE': 'value'\n"
            "  - Global (all templates): 'global.VARIABLE': 'value'\n"
            "Supports interpolation: {{global.VARIABLE}} or {{template.slug.VARIABLE}}"
        ),
    )

    disabled_templates = models.JSONField(
        default=list,
        blank=True,
        help_text="List of template slugs to disable for this academy. Example: ['welcome_academy', 'nps_survey']",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Academy Notification Settings"
        verbose_name_plural = "Academy Notification Settings"

    def __str__(self):
        return f"Notification settings for {self.academy.name}"

    def is_template_enabled(self, template_slug: str) -> bool:
        """
        Check if a template is enabled for this academy.
        
        Args:
            template_slug: The notification template slug
        
        Returns:
            bool: False if template is in disabled_templates list, True otherwise
        """
        return template_slug not in self.disabled_templates

    def get_variable_override(self, template_slug: str, variable_name: str):
        """
        Get override value for a variable.
        Priority: template-specific > global > None
        """
        # Template-specific override
        template_key = f"template.{template_slug}.{variable_name}"
        if template_key in self.template_variables:
            return self.template_variables[template_key]

        # Global override
        global_key = f"global.{variable_name}"
        if global_key in self.template_variables:
            return self.template_variables[global_key]

        return None

    def get_all_overrides_for_template(self, template_slug: str) -> dict:
        """
        Get all variable overrides for a template with interpolation support.
        Variables can reference other variables using {{global.VAR}} or {{template.slug.VAR}} syntax.
        Also supports {VARIABLE} for academy model fields (COMPANY_NAME, DOMAIN_NAME, etc).
        """
        overrides = {}

        # Collect all overrides (globals + template-specific)
        for key, value in self.template_variables.items():
            if key.startswith("global."):
                var_name = key.replace("global.", "")
                overrides[var_name] = value

        template_prefix = f"template.{template_slug}."
        for key, value in self.template_variables.items():
            if key.startswith(template_prefix):
                var_name = key.replace(template_prefix, "")
                overrides[var_name] = value

        # Resolve variable references within values (uses self.academy for {VARIABLE})
        overrides = self._resolve_variable_references(overrides, template_slug)

        return overrides

    def _resolve_variable_references(self, overrides: Dict[str, str], template_slug: str, max_depth: int = 5) -> Dict[str, str]:
        """
        Resolve variable references in override values.
        Supports:
        - {global.VAR} and {template.slug.VAR} (cross-references between settings)
        - {VARIABLE} for academy model fields (COMPANY_NAME from academy.name, etc)
        """
        resolved = {}

        for key, value in overrides.items():
            if not isinstance(value, str):
                resolved[key] = value
                continue

            # Resolve references iteratively (up to max_depth to prevent infinite loops)
            resolved_value = value
            for _ in range(max_depth):
                has_changes = False
                
                # 1. Find and replace {global.VAR} or {template.slug.VAR} references
                pattern_bracket = r'\{(global\.\w+|template\.\w+\.\w+)\}'
                matches_bracket = re.findall(pattern_bracket, resolved_value)
                
                for match in matches_bracket:
                    replacement = self._get_reference_value(match, template_slug, overrides)
                    if replacement is not None:
                        resolved_value = resolved_value.replace(f'{{{match}}}', str(replacement))
                        has_changes = True
                
                # 2. Find and replace {VARIABLE} from academy model fields
                pattern_single = r'\{([A-Z_][A-Z0-9_]*)\}'
                matches_single = re.findall(pattern_single, resolved_value)
                
                for var_name in matches_single:
                    replacement = self._get_academy_value(var_name, overrides, key)
                    if replacement is not None:
                        resolved_value = resolved_value.replace(f'{{{var_name}}}', str(replacement))
                        has_changes = True

                if not has_changes:
                    break  # No more references to resolve

            resolved[key] = resolved_value

        return resolved

    def _get_reference_value(self, reference: str, template_slug: str, overrides: Dict[str, str]):
        """
        Get the value for a variable reference.
        reference format: 'global.VAR' or 'template.slug.VAR'
        """
        if reference.startswith("global."):
            var_name = reference.replace("global.", "")
            # Check if it's in overrides (already collected)
            if var_name in overrides:
                return overrides[var_name]
            # Otherwise check raw template_variables
            return self.template_variables.get(reference)

        elif reference.startswith("template."):
            parts = reference.split(".")
            if len(parts) == 3:
                ref_slug, var_name = parts[1], parts[2]
                # Check if it's in overrides (already collected)
                if var_name in overrides:
                    return overrides[var_name]
                # Otherwise check raw template_variables
                return self.template_variables.get(reference)

        return None

    def _get_academy_value(self, var_name: str, overrides: Dict[str, str], current_key: str):
        """
        Get value for {VARIABLE} from academy model fields.
        Search order matches /v1/notify/academy/variables endpoint:
        1. overrides (from other override variables)
        2. academy model fields (academy.name, academy.website_url, etc)
        3. environment variables (fallback)
        """
        import os
        
        # 1. Check in overrides (allows referencing other override variables)
        if var_name in overrides and var_name != current_key:
            return overrides[var_name]
        
        # 2. Check in academy model fields (same as academy_values in /v1/notify/academy/variables)
        academy_field_map = {
            "COMPANY_NAME": lambda: self.academy.name,
            "COMPANY_LOGO": lambda: self.academy.logo_url,
            "COMPANY_INFO_EMAIL": lambda: self.academy.feedback_email,
            "COMPANY_LEGAL_NAME": lambda: self.academy.legal_name or self.academy.name,
            "PLATFORM_DESCRIPTION": lambda: self.academy.platform_description,
            "DOMAIN_NAME": lambda: self.academy.website_url,
        }
        
        if var_name in academy_field_map:
            try:
                value = academy_field_map[var_name]()
                if value:
                    return value
            except:
                pass
        
        # 3. Fallback to environment variables (same as system_defaults)
        env_map = {
            "API_URL": "API_URL",
            "COMPANY_NAME": "COMPANY_NAME",
            "COMPANY_CONTACT_URL": "COMPANY_CONTACT_URL",
            "COMPANY_LEGAL_NAME": "COMPANY_LEGAL_NAME",
            "COMPANY_ADDRESS": "COMPANY_ADDRESS",
            "COMPANY_INFO_EMAIL": "COMPANY_INFO_EMAIL",
            "DOMAIN_NAME": "DOMAIN_NAME",
        }
        
        if var_name in env_map:
            return os.environ.get(env_map[var_name], "")
        
        return None

    def clean(self):
        """
        Validate template_variables against registry.
        Ensures template slugs and variable names exist in the notification registry.
        """
        from breathecode.notify.utils.email_manager import EmailManager

        errors = []

        # Validate disabled_templates
        if not isinstance(self.disabled_templates, list):
            errors.append("disabled_templates must be a list")
        else:
            for template_slug in self.disabled_templates:
                if not isinstance(template_slug, str):
                    errors.append(f"Invalid disabled template: {template_slug}. Must be a string")
                    continue
                
                # Check if template exists in registry
                notification = EmailManager.get_notification(template_slug)
                if not notification:
                    errors.append(f"Disabled template '{template_slug}' not found in notification registry")

        # Validate each key in template_variables
        for key, value in self.template_variables.items():
            parts = key.split(".")

            # Validate template-specific overrides
            if key.startswith("template."):
                if len(parts) != 3:
                    errors.append(f"Invalid key format: '{key}'. Expected 'template.SLUG.VARIABLE'")
                    continue

                template_slug = parts[1]
                variable_name = parts[2]

                # Check if template exists in registry
                notification = EmailManager.get_notification(template_slug)
                if not notification:
                    errors.append(f"Template '{template_slug}' not found in notification registry")
                    continue

                # Check if variable exists in template
                var_names = [v["name"] for v in notification.get("variables", [])]
                if variable_name not in var_names:
                    errors.append(
                        f"Variable '{variable_name}' not found in template '{template_slug}'. "
                        f"Available variables: {', '.join(var_names) if var_names else 'none'}"
                    )

            # Validate global overrides
            elif key.startswith("global."):
                if len(parts) != 2:
                    errors.append(f"Invalid key format: '{key}'. Expected 'global.VARIABLE'")

            # Invalid format
            else:
                errors.append(
                    f"Invalid key format: '{key}'. Must start with 'template.' or 'global.'"
                )

        if errors:
            raise ValidationError("; ".join(errors))

        super().clean()
