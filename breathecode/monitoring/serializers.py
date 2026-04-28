import logging

from capyc.core.i18n import translation
from capyc.rest_framework.exceptions import ValidationException
from django.core.validators import URLValidator
from rest_framework import serializers

from breathecode.authenticate.models import AcademyAuthSettings
from breathecode.monitoring.actions import subscribe_repository
from breathecode.monitoring.models import MonitorScript, MonitoringError, RepositorySubscription
from breathecode.monitoring.tasks import async_subscribe_repo, async_unsubscribe_repo
from breathecode.utils import serpy

logger = logging.getLogger(__name__)


class AcademySmallSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()


class CSVDownloadSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    name = serpy.Field()
    url = serpy.Field()
    status = serpy.Field()
    status_message = serpy.Field()
    created_at = serpy.Field()
    finished_at = serpy.Field()


class CSVUploadSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    name = serpy.Field()
    url = serpy.Field()
    status = serpy.Field()
    status_message = serpy.Field()
    created_at = serpy.Field()
    finished_at = serpy.Field()


class RepoSubscriptionSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    hook_id = serpy.Field()
    repository = serpy.Field()
    token = serpy.Field()
    updated_at = serpy.Field()
    status = serpy.Field()
    status_message = serpy.Field()
    last_call = serpy.Field()
    owner = AcademySmallSerializer()


class RepositorySubscriptionSerializer(serializers.ModelSerializer):
    token = serializers.CharField(read_only=True)
    repository = serializers.CharField(required=False)
    owner = serializers.IntegerField(read_only=True)
    hook_id = serializers.IntegerField(read_only=True)
    last_call = serializers.DateTimeField(read_only=True)
    status_message = serializers.CharField(read_only=True)

    class Meta:
        model = RepositorySubscription
        fields = "__all__"

    def validate(self, data):
        academy_id = self.context["academy"]
        lang = self.context["lang"]

        # If creating
        if self.instance is None:
            if "repository" not in data or data["repository"] == "":
                raise ValidationException(
                    translation(
                        lang,
                        en="You must specify a repository url",
                        es="Debes especificar el URL del repositorio a subscribir",
                        slug="missing-repo",
                    )
                )

            url_validator = URLValidator()
            try:
                url_validator(data["repository"])
                if "github.com" not in data["repository"]:
                    raise serializers.ValidationError("Only GitHub repositories can be subscribed to")
            except serializers.ValidationError as e:
                raise ValidationException(
                    translation(
                        lang,
                        en=str(e),
                        es="La URL del repositorio debe ser valida y apuntar a github.com",
                        slug="invalid-repo-url",
                    )
                )

            subs = RepositorySubscription.objects.filter(owner__id=academy_id, repository=data["repository"]).first()
            # Sabe repo and academy subscription cannot be CREATED twice
            if subs is not None:
                raise ValidationException(
                    translation(
                        lang,
                        en="There is already another subscription for the same repository and owner, make sure you have access?",
                        es="Ya existe una subscripcion para este mismo repositorio y owner, asegurate de tener accesso",
                        slug="duplicated-repo-subscription",
                    )
                )

        # If updating
        if self.instance:
            if (
                "status" in data
                and data["status"] != self.instance.status
                and data["status"] not in ["DISABLED", "OPERATIONAL"]
            ):
                raise ValidationException(
                    translation(
                        lang,
                        en="Repo Subscription status cannot be manually set to " + data["status"],
                        es="El status de esta subscripción no puede asignarse manualmente como " + data["status"],
                        slug="cannot-manually-set-status",
                    )
                )

            if "repository" in data and data["repository"] != self.instance.repository:
                raise ValidationException(
                    translation(
                        lang,
                        en="You cannot update a subscription repository, create a new one instead",
                        es="No puedes modificar el repositorio de una subscripción, crea una nueva subscripción en su lugar",
                        slug="cannot-manually-update-repo",
                    )
                )

        return super().validate(data)

    def create(self, validated_data):
        academy_id = self.context["academy"]
        lang = self.context["lang"]

        settings = AcademyAuthSettings.objects.filter(academy__id=academy_id).first()
        if settings is None:
            raise ValidationException(
                translation(
                    lang,
                    en="Github credentials and settings have not been found for the academy",
                    es="No se han encontrado credenciales y configuración de Github para esta academia",
                    slug="github-settings-not-found",
                )
            )

        instance = super(RepositorySubscriptionSerializer, self).create(
            {
                **validated_data,
                "owner": settings.academy,
            }
        )

        try:
            subscription = subscribe_repository(instance.id, settings)
            if subscription.status != "OPERATIONAL":
                raise Exception(subscription.status_message)
        except Exception as e:
            logger.error(str(e))
            raise ValidationException(
                translation(
                    lang,
                    en=str(e),
                    es="Error al intentar subscribirse al repositorio, revisa la subscripción para mas detalles",
                    slug="github-error",
                )
            )

        return instance

    def update(self, instance, validated_data):
        if instance.status == "DISABLED" and validated_data["status"] == "OPERATIONAL":
            async_subscribe_repo.delay(instance.id)

        elif instance.status == "OPERATIONAL" and validated_data["status"] == "DISABLED":
            async_unsubscribe_repo.delay(instance.id, force_delete=False)

        return super().update(instance, validated_data)


class MonitoringErrorSerializer(serpy.Serializer):
    id = serpy.Field()
    severity = serpy.Field()
    title = serpy.Field()
    description = serpy.Field()
    details = serpy.Field()
    comments = serpy.Field()
    created_at = serpy.Field()
    fixed_at = serpy.Field()
    replicated_at = serpy.Field()
    monitor_script_id = serpy.Field(attr="monitor_script.id")
    academy_id = serpy.Field(attr="academy.id")
    user_id = serpy.Field(attr="user.id", required=False)


class MonitorScriptSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    script_slug = serpy.Field()
    status = serpy.Field()
    status_code = serpy.Field()
    severity_level = serpy.Field()
    status_text = serpy.Field()
    special_status_text = serpy.Field()
    response_text = serpy.Field()
    last_run = serpy.Field()
    created_at = serpy.Field()
    updated_at = serpy.Field()


class ChurnRiskReportListSerializer(serpy.Serializer):
    id = serpy.Field()
    user_id = serpy.Field(attr="user.id")
    user_email = serpy.Field(attr="user.email")
    academy_id = serpy.Field(attr="academy.id", required=False)
    report_date = serpy.Field()
    churn_risk_score = serpy.Field()
    risk_level = serpy.Field()
    days_since_last_activity = serpy.Field()
    login_count_7d = serpy.Field()
    assignments_completed_7d = serpy.Field()
    has_payment_issues = serpy.Field()
    subscription_status = serpy.Field()


class ChurnRiskReportDetailSerializer(serpy.Serializer):
    id = serpy.Field()
    user_id = serpy.Field(attr="user.id")
    user_email = serpy.Field(attr="user.email")
    academy_id = serpy.Field(attr="academy.id", required=False)
    report_date = serpy.Field()
    churn_risk_score = serpy.Field()
    risk_level = serpy.Field()
    days_since_last_activity = serpy.Field()
    login_count_7d = serpy.Field()
    login_trend = serpy.Field()
    assignments_completed_7d = serpy.Field()
    assignment_trend = serpy.Field()
    avg_frustration_score = serpy.Field()
    avg_engagement_score = serpy.Field()
    has_payment_issues = serpy.Field()
    subscription_status = serpy.Field()
    days_until_renewal = serpy.Field()
    details = serpy.Field()
    created_at = serpy.Field()


class ChurnReportSummarySerializer(serpy.Serializer):
    total = serpy.Field()
    average_score = serpy.Field()
    payment_risk_count = serpy.Field()
    unresolved_alert_count = serpy.Field()
    risk_levels = serpy.Field()


class AcquisitionReportListSerializer(serpy.Serializer):
    id = serpy.Field()
    source_type = serpy.Field()
    source_id = serpy.Field()
    report_date = serpy.Field()
    academy_id = serpy.Field(attr="academy.id")
    user_id = serpy.Field(required=False)
    email = serpy.Field()
    funnel_tier = serpy.Field()
    utm_source = serpy.Field(required=False)
    utm_medium = serpy.Field(required=False)
    utm_campaign = serpy.Field(required=False)
    landing_url = serpy.Field(required=False)
    conversion_url = serpy.Field(required=False)
    asset_slug = serpy.Field(required=False)
    event_slug = serpy.Field(required=False)
    deal_status = serpy.Field(required=False)
    lead_type = serpy.Field(required=False)
    team_seat_invite = serpy.Field()


class AcquisitionReportDetailSerializer(serpy.Serializer):
    id = serpy.Field()
    source_type = serpy.Field()
    source_id = serpy.Field()
    report_date = serpy.Field()
    academy_id = serpy.Field(attr="academy.id")
    user_id = serpy.Field(required=False)
    email = serpy.Field()
    funnel_tier = serpy.Field()
    utm_source = serpy.Field(required=False)
    utm_medium = serpy.Field(required=False)
    utm_campaign = serpy.Field(required=False)
    utm_term = serpy.Field(required=False)
    utm_content = serpy.Field(required=False)
    utm_placement = serpy.Field(required=False)
    landing_url = serpy.Field(required=False)
    conversion_url = serpy.Field(required=False)
    lead_type = serpy.Field(required=False)
    deal_status = serpy.Field(required=False)
    attribution_id = serpy.Field(required=False)
    event_slug = serpy.Field(required=False)
    asset_slug = serpy.Field(required=False)
    course_id = serpy.Field(required=False)
    cohort_id = serpy.Field(required=False)
    syllabus_id = serpy.Field(required=False)
    role_id = serpy.Field(required=False)
    author_id = serpy.Field(required=False)
    subscription_seat_id = serpy.Field(required=False)
    plan_financing_seat_id = serpy.Field(required=False)
    payment_method_id = serpy.Field(required=False)
    team_seat_invite = serpy.Field()
    details = serpy.Field()
    created_at = serpy.Field()


class AcquisitionReportSummarySerializer(serpy.Serializer):
    total = serpy.Field()
    by_source_type = serpy.Field()
    by_funnel_tier = serpy.Field()
    by_funnel_tier_label = serpy.Field()
    top_asset_slugs = serpy.Field()
    top_event_slugs = serpy.Field()
    top_utm_sources = serpy.Field()
    top_utm_campaigns = serpy.Field()
    top_conversion_urls = serpy.Field()
    by_deal_status = serpy.Field()
    team_seat_invite_count = serpy.Field()


class MonitoringReportTypeSerializer(serpy.Serializer):
    slug = serpy.Field()
    label = serpy.Field()
    description = serpy.Field()
    filters = serpy.Field()
    sort_fields = serpy.Field()
    supports_detail = serpy.Field()
    supports_summary = serpy.Field()


class MonitorScriptSmallSerializer(serpy.Serializer):
    """Basic MonitorScript serializer."""
    
    id = serpy.Field()
    script_slug = serpy.Field()
    status = serpy.Field()
    status_code = serpy.Field()
    severity_level = serpy.Field()
    status_text = serpy.Field()
    special_status_text = serpy.Field()
    response_text = serpy.Field()
    last_run = serpy.Field()
    created_at = serpy.Field()
    updated_at = serpy.Field()
