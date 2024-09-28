from collections import OrderedDict
from typing import Literal, Optional

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

__all__ = ["UserProxy", "CohortProxy", "Device", "SlackTeam", "SlackUser", "SlackUserTeam", "SlackChannel", "Hook"]
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
            self.sent_at = timezone.now()

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
            self._send_notification()

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
