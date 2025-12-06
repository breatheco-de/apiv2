from capyc.rest_framework.exceptions import ValidationException
from django.conf import settings
from rest_framework import serializers

from breathecode.admissions.models import Academy
from breathecode.authenticate.serializers import GetSmallAcademySerializer
from breathecode.utils import serpy

from .models import AcademyNotifySettings, Hook, HookError


class UserSerializer(serpy.Serializer):
    id = serpy.Field()
    first_name = serpy.Field()
    last_name = serpy.Field()


class DeviceSerializer(serpy.Serializer):
    id = serpy.Field()
    registration_id = serpy.Field()
    created_at = serpy.Field()


class HookSerializer(serializers.ModelSerializer):

    class Meta:
        model = Hook
        read_only_fields = ("user",)
        exclude = ["sample_data"]

    def validate(self, data):

        if data["event"] not in settings.HOOK_EVENTS:
            err_msg = "Unexpected event {}".format(data["event"])
            raise ValidationException(err_msg, slug="invalid-event")

        # superadmins can subscribe to any hook without needed an academy token
        if not self.context["request"].user.is_superuser:
            academy = Academy.objects.filter(slug=self.context["request"].user.username).first()
            if academy is None:
                raise ValidationException("No valid academy token found", slug="invalid-academy-token")

        data["user"] = self.context["request"].user

        return super().validate(data)


class SlackTeamSerializer(serpy.Serializer):
    id = serpy.Field()
    slack_id = serpy.Field()
    name = serpy.Field()
    academy = GetSmallAcademySerializer(required=False)
    created_at = serpy.Field()
    sync_status = serpy.Field()
    sync_message = serpy.Field()


class NotificationSerializer(serpy.Serializer):
    id = serpy.Field()
    message = serpy.Field()
    status = serpy.Field()
    type = serpy.Field()
    academy = GetSmallAcademySerializer(required=False)
    meta = serpy.Field()
    sent_at = serpy.Field()
    done_at = serpy.Field()
    seen_at = serpy.Field()


class AcademyNotifySettingsSerializer(serializers.ModelSerializer):
    """Serializer for managing academy notification settings."""

    class Meta:
        model = AcademyNotifySettings
        fields = ["academy", "template_variables", "disabled_templates", "created_at", "updated_at"]
        read_only_fields = ["academy", "created_at", "updated_at"]

    def validate_template_variables(self, value):
        """
        Validate template_variables field.
        Creates a temporary instance to run model's clean() validation.
        """
        if not isinstance(value, dict):
            raise serializers.ValidationError("template_variables must be a dictionary")

        # Create temporary instance for validation
        temp_instance = AcademyNotifySettings(template_variables=value)
        
        # If updating, set the academy from the instance
        if self.instance:
            temp_instance.academy = self.instance.academy
        
        try:
            temp_instance.clean()
        except ValidationException as e:
            raise serializers.ValidationError(str(e))

        return value


class AcademyNotifySettingsSmallSerializer(serpy.Serializer):
    """Small serializer for read-only academy notification settings."""

    template_variables = serpy.Field()
    disabled_templates = serpy.Field()
    created_at = serpy.Field()
    updated_at = serpy.Field()


class HookErrorSerializer(serpy.Serializer):
    """Serializer for HookError model."""

    id = serpy.Field()
    message = serpy.Field()
    event = serpy.Field()
    created_at = serpy.Field()
    updated_at = serpy.Field()
    hooks = serpy.MethodField()

    def get_hooks(self, obj):
        """Return list of hook IDs associated with this error."""
        return [hook.id for hook in obj.hooks.all()]
