import re
from typing import Any, Dict

from capyc.core.i18n import translation
from capyc.rest_framework.exceptions import ValidationException
from rest_framework import serializers

from breathecode.utils import serpy

from .models import (
    ProvisioningAcademy,
    ProvisioningBill,
    ProvisioningContainer,
    ProvisioningProfile,
    ProvisioningVPS,
    ProvisioningVendor,
)


class AcademySerializer(serpy.Serializer):
    """The serializer schema definition."""

    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    name = serpy.Field()
    slug = serpy.Field()


class UserTinySerializer(serpy.Serializer):
    """Minimal user payload for nested provisioning responses."""

    id = serpy.Field()
    email = serpy.Field()
    first_name = serpy.Field()
    last_name = serpy.Field()


class AcademyBillDetailSerializer(serpy.Serializer):
    """Enhanced academy serializer for bill detail view."""

    id = serpy.Field()
    name = serpy.Field()
    slug = serpy.Field()
    feedback_email = serpy.Field()
    legal_name = serpy.Field()
    logo_url = serpy.Field()


class ContainerMeSmallSerializer(serpy.Serializer):
    """The serializer schema definition."""

    # Use a Field subclass like IntField if you need more validation.
    web_url = serpy.Field()
    status = serpy.Field()
    display_name = serpy.Field()
    last_used_at = serpy.Field()
    has_unpushed_changes = serpy.Field()
    has_uncommitted_changes = serpy.Field()
    task_associated_slug = serpy.Field()


class ContainerMeBigSerializer(serpy.Serializer):
    """The serializer schema definition."""

    # Use a Field subclass like IntField if you need more validation.
    web_url = serpy.Field()
    status = serpy.Field()
    display_name = serpy.Field()
    last_used_at = serpy.Field()
    provisioned_at = serpy.Field()
    has_unpushed_changes = serpy.Field()
    has_uncommitted_changes = serpy.Field()
    branch_name = serpy.Field()
    task_associated_slug = serpy.Field()
    created_at = serpy.Field()


class GetProvisioningVendorSerializer(serpy.Serializer):
    id = serpy.Field()
    name = serpy.Field()
    workspaces_url = serpy.Field()
    settings_schema = serpy.MethodField()

    def get_settings_schema(self, obj):
        return get_vendor_settings_schema(getattr(obj, "name", ""))


class GetProvisioningBillSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    vendor = GetProvisioningVendorSerializer(required=False)
    total_amount = serpy.Field()
    status = serpy.Field()
    title = serpy.Field()
    status_details = serpy.Field()
    paid_at = serpy.Field()
    fee = serpy.Field()
    stripe_url = serpy.Field()
    created_at = serpy.Field()


class GetProvisioningBillSerializer(serpy.Serializer):
    id = serpy.Field()
    vendor = GetProvisioningVendorSerializer(required=False)
    total_amount = serpy.Field()
    status = serpy.Field()
    status_details = serpy.Field()
    paid_at = serpy.Field()
    fee = serpy.Field()
    stripe_url = serpy.Field()
    created_at = serpy.Field()
    title = serpy.Field()


class GetProvisioningBillDetailSerializer(serpy.Serializer):
    id = serpy.Field()
    vendor = GetProvisioningVendorSerializer(required=False)
    total_amount = serpy.Field()
    status = serpy.Field()
    status_details = serpy.Field()
    paid_at = serpy.Field()
    fee = serpy.Field()
    stripe_url = serpy.Field()
    created_at = serpy.Field()
    title = serpy.Field()
    academy = AcademyBillDetailSerializer(required=False)
    status_display = serpy.MethodField()
    upload_task = serpy.MethodField()

    def get_status_display(self, obj):
        status_map = {
            "DUE": "UNDER_REVIEW",
            "APPROVED": "READY_TO_PAY",
            "PAID": "ALREADY PAID",
            "PENDING": "PENDING",
        }
        return status_map.get(obj.status, obj.status)

    def get_upload_task(self, obj):
        if not obj.hash:
            return None

        from task_manager.models import TaskManager

        # Filter by task module, name, and check if first argument matches hash
        tasks = TaskManager.objects.filter(
            task_module="breathecode.provisioning.tasks", task_name="upload"
        )

        # Check each task's arguments to find matching hash
        for task in tasks:
            if task.arguments and task.arguments.get("args") and len(task.arguments["args"]) > 0:
                if task.arguments["args"][0] == obj.hash:
                    # Format datetime fields to ISO format
                    def format_datetime(dt):
                        if dt is None:
                            return None
                        return dt.isoformat()

                    return {
                        "id": task.id,
                        "status": task.status,
                        "status_message": task.status_message,
                        "task_id": task.task_id,
                        "last_run": format_datetime(task.last_run),
                        "started_at": format_datetime(task.started_at),
                        "attempts": task.attempts,
                        "current_page": task.current_page,
                        "total_pages": task.total_pages,
                        "priority": task.priority,
                        "killed": task.killed,
                        "fixed": task.fixed,
                        "exception_module": task.exception_module,
                        "exception_name": task.exception_name,
                        "created_at": format_datetime(task.created_at),
                        "updated_at": format_datetime(task.updated_at),
                    }

        return None


class GetProvisioningProfile(serpy.Serializer):
    id = serpy.Field()
    vendor = GetProvisioningVendorSerializer(required=False)
    academy = AcademySerializer(required=False)
    cohort_ids = serpy.MethodField()
    member_ids = serpy.MethodField()

    def get_cohort_ids(self, obj):
        return list(obj.cohorts.values_list("id", flat=True))

    def get_member_ids(self, obj):
        return list(obj.members.values_list("id", flat=True))


class ProvisioningProfileCreateUpdateSerializer(serializers.Serializer):
    """Request body for POST/PUT provisioning profile."""

    vendor_id = serializers.IntegerField(required=True)
    cohort_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True,
        default=list,
    )
    member_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True,
        default=list,
    )


class GetProvisioningConsumptionKindSerializer(serpy.Serializer):
    id = serpy.Field()
    product_name = serpy.Field()
    sku = serpy.Field()


class GetProvisioningUserConsumptionSerializer(serpy.Serializer):
    id = serpy.Field()
    kind = GetProvisioningConsumptionKindSerializer(required=False)
    username = serpy.Field()
    quantity = serpy.Field()
    amount = serpy.Field()
    processed_at = serpy.Field()
    status = serpy.Field()


class GetProvisioningUserConsumptionDetailSerializer(serpy.Serializer):
    username = serpy.Field()
    status = serpy.Field()
    status_text = serpy.Field()
    amount = serpy.Field()
    kind = GetProvisioningConsumptionKindSerializer(required=False)


class ProvisioningContainerSerializer(serializers.ModelSerializer):
    # slug = serializers.CharField(required=False, default=None)

    class Meta:
        model = ProvisioningContainer
        include = (
            "task_associated_slug",
            "has_uncommitted_changes",
            "branch_name",
            "destination_status",
            "destination_status_text",
        )

    def validate(self, data):

        if "slug" in data and data["slug"] is not None:

            if not re.match(r"^[-\w]+$", data["slug"]):
                raise ValidationException(
                    f'Invalid link slug {data["slug"]}, should only contain letters, numbers and slash "-"',
                    slug="invalid-slug-format",
                )

        # NOTE: this have the propertly academy but it's not defined here
        return data

    def create(self, validated_data):
        from breathecode.marketing.models import ShortLink

        return ShortLink.objects.create(**validated_data, author=self.context.get("request").user)


class ProvisioningConsumptionKindHTMLSerializer(serpy.Serializer):
    product_name = serpy.Field()
    sku = serpy.Field()


class ProvisioningConsumptionEventHTMLSerializer(serpy.Serializer):
    username = serpy.Field()
    status = serpy.Field()
    status_text = serpy.Field()
    kind = ProvisioningConsumptionKindHTMLSerializer(required=False)


class ProvisioningUserConsumptionHTMLResumeSerializer(serpy.Serializer):
    username = serpy.Field()
    status = serpy.Field()
    status_text = serpy.Field()
    amount = serpy.Field()
    kind = ProvisioningConsumptionKindHTMLSerializer(required=False)


class ProvisioningUserConsumptionHTMLSerializer(serpy.Serializer):
    username = serpy.Field()
    status = serpy.Field()
    status_text = serpy.Field()
    kind = ProvisioningConsumptionKindHTMLSerializer(required=False)

    events = serpy.MethodField()

    def get_events(self, obj):
        ProvisioningConsumptionEventHTMLSerializer(obj.events, many=True).data


class ProvisioningBillHTMLSerializer(serpy.Serializer):

    id = serpy.Field()
    total_amount = serpy.Field()
    academy = AcademySerializer(required=False)
    status = serpy.Field()
    paid_at = serpy.Field()
    created_at = serpy.Field()
    title = serpy.Field()
    stripe_url = serpy.Field()


class ProvisioningBillSerializer(serializers.ModelSerializer):

    class Meta:
        model = ProvisioningBill
        fields = ("status",)

    def validate(self, data):

        if self.instance and "status" in data and self.instance.status in ["PENDING", "ERROR"]:
            status = data["status"].lower()
            raise ValidationException(
                translation(
                    self.context["lang"],
                    en=f"You cannot change the status of this bill due to it is marked as {status}",
                    es="No puedes cambiar el estado de esta factura debido a que esta marcada " f"como {status}",
                    slug="readonly-bill-status",
                ),
                code=400,
            )

        if self.instance and "status" in data and data["status"] in ["PENDING", "ERROR"]:
            status = data["status"].lower()
            raise ValidationException(
                translation(
                    self.context["lang"],
                    en=f"You cannot set the status of this bill to {status} because this status is " "forbidden",
                    es=f"No puedes cambiar el estado de esta factura a {status} porque este estado esta " "prohibido",
                    slug="invalid-bill-status",
                ),
                code=400,
            )

        return data


# --- VPS serializers ---


class VPSListSerializer(serpy.Serializer):
    """VPS list item (no root_password)."""

    id = serpy.Field()
    status = serpy.Field()
    hostname = serpy.Field()
    ip_address = serpy.Field()
    ssh_user = serpy.Field()
    ssh_port = serpy.Field()
    plan_slug = serpy.Field()
    error_message = serpy.Field()
    requested_at = serpy.Field()
    provisioned_at = serpy.Field()
    deleted_at = serpy.Field()
    created_at = serpy.Field()
    updated_at = serpy.Field()


class VPSDetailSerializer(serpy.Serializer):
    """VPS detail; include root_password only when context has show_password=True (owner)."""

    id = serpy.Field()
    status = serpy.Field()
    hostname = serpy.Field()
    ip_address = serpy.Field()
    ssh_user = serpy.Field()
    ssh_port = serpy.Field()
    plan_slug = serpy.Field()
    error_message = serpy.Field()
    requested_at = serpy.Field()
    provisioned_at = serpy.Field()
    deleted_at = serpy.Field()
    created_at = serpy.Field()
    updated_at = serpy.Field()
    root_password = serpy.MethodField()

    def get_root_password(self, obj):
        if not (self.context or {}).get("show_password"):
            return None
        from breathecode.utils.encryption import decrypt
        if not obj.root_password_encrypted:
            return None
        try:
            return decrypt(obj.root_password_encrypted)
        except Exception:
            return None


class VPSRequestSerializer(serializers.Serializer):
    """Request body for POST me/vps (optional plan_slug)."""

    class VendorSelectionSerializer(serializers.Serializer):
        item_id = serializers.CharField(required=False, allow_blank=False, max_length=100)
        template_id = serializers.IntegerField(required=False, min_value=1)
        data_center_id = serializers.IntegerField(required=False, min_value=1)

    plan_slug = serializers.CharField(required=False, allow_blank=True, max_length=100)
    vendor_selection = VendorSelectionSerializer(required=False)


class AcademyVPSCreateSerializer(serializers.Serializer):
    """Request body for POST academy/vps (staff provisions VPS for a student)."""

    class VendorSelectionSerializer(serializers.Serializer):
        item_id = serializers.CharField(required=False, allow_blank=False, max_length=100)
        template_id = serializers.IntegerField(required=False, min_value=1)
        data_center_id = serializers.IntegerField(required=False, min_value=1)

    user_id = serializers.IntegerField(required=True, min_value=1)
    plan_slug = serializers.CharField(required=False, allow_blank=True, max_length=100)
    vendor_selection = VendorSelectionSerializer(required=False)


class AcademyVPSListSerializer(serpy.Serializer):
    """Academy VPS report row (user info, no root_password)."""

    id = serpy.Field()
    status = serpy.Field()
    hostname = serpy.Field()
    ip_address = serpy.Field()
    ssh_user = serpy.Field()
    ssh_port = serpy.Field()
    plan_slug = serpy.Field()
    error_message = serpy.Field()
    requested_at = serpy.Field()
    provisioned_at = serpy.Field()
    deleted_at = serpy.Field()
    created_at = serpy.Field()
    user = UserTinySerializer(required=False)


# --- Provisioning academy (credentials and settings) ---


class GetProvisioningAcademySerializer(serpy.Serializer):
    """Response for ProvisioningAcademy; credentials never returned, only credentials_set flag."""

    id = serpy.Field()
    vendor = GetProvisioningVendorSerializer(required=False)
    academy_id = serpy.Field()
    credentials_set = serpy.MethodField()
    vendor_settings = serpy.Field()
    container_idle_timeout = serpy.Field()
    max_active_containers = serpy.Field()
    created_at = serpy.Field()
    updated_at = serpy.Field()

    def get_credentials_set(self, obj):
        return bool(obj.credentials_token or obj.credentials_key)


class ProvisioningAcademyCreateSerializer(serializers.Serializer):
    """Request body for POST provisioning academy config."""

    vendor_id = serializers.IntegerField(required=True)
    credentials_token = serializers.CharField(required=True, max_length=200, allow_blank=False)
    credentials_key = serializers.CharField(required=False, max_length=200, allow_blank=True, default="")
    vendor_settings = serializers.JSONField(required=False, default=dict)
    container_idle_timeout = serializers.IntegerField(required=False, default=15, min_value=1)
    max_active_containers = serializers.IntegerField(required=False, default=2, min_value=1)
    allowed_machine_type_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True,
        default=list,
    )


class ProvisioningAcademyUpdateSerializer(serializers.Serializer):
    """Request body for PUT provisioning academy config (all optional)."""

    credentials_token = serializers.CharField(required=False, max_length=200, allow_blank=True)
    credentials_key = serializers.CharField(required=False, max_length=200, allow_blank=True)
    vendor_settings = serializers.JSONField(required=False)
    container_idle_timeout = serializers.IntegerField(required=False, min_value=1)
    max_active_containers = serializers.IntegerField(required=False, min_value=1)
    allowed_machine_type_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True,
    )


def get_vendor_settings_schema(vendor_name: str) -> Dict[str, Any]:
    slug = (vendor_name or "").lower().strip()
    if slug != "hostinger":
        return {"fields": []}

    return {
        "fields": [
            {
                "key": "item_ids",
                "label": "Allowed catalog item IDs",
                "type": "list[string]",
                "required": True,
                "help_text": "Allowed Hostinger VPS catalog items for this academy.",
            },
            {
                "key": "template_ids",
                "label": "Allowed template IDs",
                "type": "list[integer]",
                "required": True,
                "help_text": "Allowed Hostinger OS template IDs for this academy.",
            },
            {
                "key": "data_center_ids",
                "label": "Allowed data center IDs",
                "type": "list[integer]",
                "required": True,
                "help_text": "Allowed Hostinger data center IDs for this academy.",
            },
        ]
    }


def validate_vendor_settings(vendor_name: str, vendor_settings: Dict[str, Any], *, lang: str = "en") -> Dict[str, Any]:
    slug = (vendor_name or "").lower().strip()
    settings = vendor_settings or {}
    if not isinstance(settings, dict):
        raise ValidationException(
            translation(
                lang,
                en="vendor_settings must be a JSON object.",
                es="vendor_settings debe ser un objeto JSON.",
                slug="invalid-vendor-settings",
            ),
            code=400,
        )

    if slug != "hostinger":
        return settings

    # Allow creating/updating a Hostinger academy config before the allowlists are filled.
    # The VPS request flow will enforce that allowlists exist and are non-empty at request-time.
    if not settings:
        return settings

    allowed_keys = {"item_ids", "template_ids", "data_center_ids"}
    unknown = sorted(set(settings.keys()) - allowed_keys)
    if unknown:
        raise ValidationException(
            translation(
                lang,
                en=f"Unknown vendor_settings keys: {', '.join(unknown)}.",
                es=f"Claves desconocidas en vendor_settings: {', '.join(unknown)}.",
                slug="invalid-vendor-settings-keys",
            ),
            code=400,
        )

    def _require_list(key: str, cast):
        values = settings.get(key)
        if values is None or not isinstance(values, list) or len(values) == 0:
            raise ValidationException(
                translation(
                    lang,
                    en=f"{key} must be a non-empty list.",
                    es=f"{key} debe ser una lista no vacia.",
                    slug="invalid-vendor-settings-value",
                ),
                code=400,
            )
        normalized = []
        for value in values:
            try:
                casted = cast(value)
            except (TypeError, ValueError):
                raise ValidationException(
                    translation(
                        lang,
                        en=f"{key} contains an invalid value: {value}.",
                        es=f"{key} contiene un valor invalido: {value}.",
                        slug="invalid-vendor-settings-value",
                    ),
                    code=400,
                )
            normalized.append(casted)
        settings[key] = sorted(set(normalized))

    _require_list("item_ids", lambda v: str(v).strip())
    if any(not x for x in settings["item_ids"]):
        raise ValidationException(
            translation(
                lang,
                en="item_ids cannot contain blank values.",
                es="item_ids no puede contener valores vacios.",
                slug="invalid-vendor-settings-value",
            ),
            code=400,
        )

    _require_list("template_ids", int)
    _require_list("data_center_ids", int)
    return settings
