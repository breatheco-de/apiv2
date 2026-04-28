import logging
import os
from hashlib import sha256
import json
from datetime import date

import stripe
from capyc.core.i18n import translation
from capyc.rest_framework.exceptions import ValidationException
from circuitbreaker import CircuitBreakerError
from django.db.models import Q
from django.http import HttpRequest, StreamingHttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from breathecode.admissions.models import Academy
from breathecode.authenticate.actions import get_user_language
from breathecode.monitoring import signals
from breathecode.monitoring.reports.api_registry import get_report_api_config, get_report_type_metadata, resolve_default_date
from breathecode.utils import GenerateLookupsMixin, capable_of
from breathecode.utils.api_view_extensions.api_view_extensions import APIViewExtensions

from .actions import add_github_webhook, add_stripe_webhook, add_stripe_webhook_error, get_admin_actions, run_script
from .models import CSVDownload, CSVUpload, MonitorScript, ReportGenerationJob, RepositorySubscription, RepositoryWebhook
from .serializers import (
    CSVDownloadSmallSerializer,
    CSVUploadSmallSerializer,
    MonitoringErrorSerializer,
    ReportGenerationJobListSerializer,
    ReportGenerationJobSerializer,
    ReportGenerationTriggerSerializer,
    MonitorScriptSmallSerializer,
    RepositorySubscriptionSerializer,
    RepoSubscriptionSmallSerializer,
)
from .signals import github_webhook
from .tasks import async_unsubscribe_repo, generate_report_job

logger = logging.getLogger(__name__)


QUERY_PARAM_ALLOWLIST = {"limit", "offset", "sort"}


def _get_report_api_config_or_404(report_type: str, lang: str):
    config = get_report_api_config(report_type)
    if config is None:
        raise ValidationException(
            translation(
                lang,
                en=f"Report type {report_type} is not supported",
                es=f"El tipo de reporte {report_type} no está soportado",
                slug="report-type-not-found",
            ),
            code=status.HTTP_404_NOT_FOUND,
        )

    return config


def _parse_filter_value(key: str, raw_value: str, filter_config: dict, lang: str):
    filter_type = filter_config.get("type")

    try:
        if filter_type == "int":
            return int(raw_value)

        if filter_type == "float":
            return float(raw_value)

        if filter_type == "date":
            return date.fromisoformat(raw_value)

        return raw_value

    except (TypeError, ValueError):
        raise ValidationException(
            translation(
                lang,
                en=f"Invalid value for filter {key}",
                es=f"Valor inválido para el filtro {key}",
                slug="invalid-filter-value",
            ),
        )


def _validate_filter_query_params(request, config, lang: str):
    allowed_query_params = set(config.filters.keys()) | QUERY_PARAM_ALLOWLIST
    unexpected_query_params = [key for key in request.GET.keys() if key not in allowed_query_params]
    if unexpected_query_params:
        formatted = ", ".join(sorted(unexpected_query_params))
        raise ValidationException(
            translation(
                lang,
                en=f"Unsupported filters: {formatted}",
                es=f"Filtros no soportados: {formatted}",
                slug="unsupported-filter",
            ),
        )


def _validate_sort_fields(request, config, lang: str):
    if "sort" not in request.GET:
        return

    sort_values = []
    for value in request.GET.getlist("sort"):
        sort_values += [v.strip() for v in value.split(",") if v.strip()]

    for sort_field in sort_values:
        if sort_field not in config.sort_fields:
            raise ValidationException(
                translation(
                    lang,
                    en=f"Sort field {sort_field} is not allowed for report {config.slug}",
                    es=f"El campo de ordenamiento {sort_field} no está permitido para el reporte {config.slug}",
                    slug="invalid-sort-field",
                ),
            )


def _apply_report_filters(request, queryset, config, academy_id: int, lang: str):
    queryset = queryset.filter(academy_id=academy_id)

    if request.GET.get("academy"):
        academy_filter = _parse_filter_value("academy", request.GET.get("academy"), {"type": "int"}, lang)
        if academy_filter != academy_id:
            raise ValidationException(
                translation(
                    lang,
                    en="The academy query param must match the authenticated academy scope",
                    es="El parámetro academy debe coincidir con el alcance de academia autenticado",
                    slug="academy-filter-mismatch",
                ),
            )

    for key, filter_config in config.filters.items():
        if key == "academy":
            continue

        if key not in request.GET:
            continue

        value = _parse_filter_value(key, request.GET.get(key), filter_config, lang)
        if "choices" in filter_config and value not in filter_config["choices"]:
            raise ValidationException(
                translation(
                    lang,
                    en=f"Invalid value for {key}, expected one of: {', '.join(filter_config['choices'])}",
                    es=f"Valor inválido para {key}, se esperaba uno de: {', '.join(filter_config['choices'])}",
                    slug="invalid-filter-choice",
                ),
            )

        queryset = queryset.filter(**{filter_config["lookup"]: value})

    has_date_range = "date_start" in request.GET or "date_end" in request.GET
    if "date" not in request.GET and not has_date_range and config.date_field:
        latest_date = resolve_default_date(queryset, config.date_field)
        if latest_date:
            queryset = queryset.filter(**{config.date_field: latest_date})

    return queryset


def _get_filtered_report_queryset(request, report_type: str, academy_id: int, lang: str):
    config = _get_report_api_config_or_404(report_type, lang)
    queryset = config.model.objects.all()

    _validate_filter_query_params(request, config, lang)
    _validate_sort_fields(request, config, lang)

    queryset = _apply_report_filters(request, queryset, config, academy_id, lang)
    return queryset, config


async def _async_iter_from_list(items):
    """Convert a list to an async generator for StreamingHttpResponse in ASGI mode"""
    for item in items:
        yield item

def get_stripe_webhook_secret(payload=None):
    """
    Get appropriate Stripe webhook secret based on payload data.

    If payload is provided, tries to identify the academy from the webhook data
    and return its specific secret. Falls back to global secret if academy
    cannot be identified.

    Args:
        payload: Optional webhook payload (bytes or dict)

    Returns:
        str: The webhook secret or None if no secret found
    """
    import json
    import logging

    from breathecode.payments.models import AcademyPaymentSettings, Invoice

    logger = logging.getLogger(__name__)

    if payload:
        try:
            if isinstance(payload, bytes):
                payload_dict = json.loads(payload.decode("utf-8"))
            else:
                payload_dict = payload

            event_data = payload_dict.get("data", {}).get("object", {})
            charge_id = event_data.get("id")

            if charge_id:
                invoice = (
                    Invoice.objects.filter(stripe_id=charge_id).select_related("academy__payment_settings").first()
                )
                if invoice and invoice.academy:
                    academy_settings = (
                        AcademyPaymentSettings.objects.filter(
                            academy=invoice.academy, stripe_webhook_secret__isnull=False
                        )
                        .exclude(stripe_webhook_secret="")
                        .first()
                    )

                    if academy_settings and academy_settings.stripe_webhook_secret:
                        logger.info(f"Using webhook secret for academy: {invoice.academy.slug}")
                        return academy_settings.stripe_webhook_secret
        except Exception as e:
            logger.debug(f"Could not identify academy from payload: {e}")
            # Continue to fallback to global

    global_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    if global_secret:
        logger.info("Using global webhook secret")
        return global_secret

    return None


class DjangoAdminView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request: HttpRequest):
        registry = get_admin_actions()
        return Response(dict([(k, v.serialize()) for k, v in registry.items()]))

    def post(self, request: HttpRequest):

        arguments = request.data.get("arguments", {})
        if not isinstance(arguments, dict):
            raise ValidationException("Arguments must be a dictionary", slug="arguments-must-be-a-dictionary")

        registry = get_admin_actions()

        model_admin = request.data.get("model_admin", "")
        if model_admin not in registry:
            raise ValidationException(f"Model admin {model_admin} not found", slug="model-admin-not-found")

        model_admin = registry[model_admin]

        action = request.data.get("action", "")
        if action not in model_admin.actions:
            raise ValidationException(f"Action {action} not found", slug="action-not-found")

        action = model_admin.actions.get(action)

        model = model_admin.model
        model_admin = model_admin.model_admin

        try:
            qs = model.objects.filter(**arguments)
            action(model_admin, request, qs)

        except Exception as e:
            raise ValidationException(f"Error at processing action {action}: {e}", slug="action-error")

        return Response({"success": True})


@api_view(["GET"])
@permission_classes([AllowAny])
def get_endpoints(request):
    return Response([], status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([AllowAny])
def get_apps(request):
    return Response([], status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([AllowAny])
def get_download(request, download_id=None):
    lang = get_user_language(request)

    # if request.user.is_staff == False:
    #     raise ValidationException("You are not authorized to review this download",
    #                               code=status.HTTP_401_UNAUTHORIZED)

    if download_id is not None:
        download = CSVDownload.objects.filter(id=download_id).first()
        if download is None:
            raise ValidationException(f"CSV Download {download_id} not found", code=status.HTTP_404_NOT_FOUND)

        raw = request.GET.get("raw", "")
        if raw == "true":
            import os

            from ..services.google_cloud import Storage

            try:
                storage = Storage()
                cloud_file = storage.file(os.getenv("DOWNLOADS_BUCKET", None), download.name)
                buffer = cloud_file.stream_download()

            except CircuitBreakerError:
                raise ValidationException(
                    translation(
                        lang,
                        en="The circuit breaker is open due to an error, please try again later",
                        es="El circuit breaker está abierto debido a un error, por favor intente más tarde",
                        slug="circuit-breaker-open",
                    ),
                    slug="circuit-breaker-open",
                    data={"service": "Google Cloud Storage"},
                    silent=True,
                    code=503,
                )

            return StreamingHttpResponse(
                _async_iter_from_list(buffer.all()),
                content_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename={download.name}"},
            )
        else:
            serializer = CSVDownloadSmallSerializer(download, many=False)
            return Response(serializer.data, status=status.HTTP_200_OK)

    csv = CSVDownload.objects.all()
    serializer = CSVDownloadSmallSerializer(csv, many=True)

    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([AllowAny])
def get_upload(request, upload_id=None):

    # if request.user.is_staff == False:
    #     raise ValidationException("You are not authorized to review this download",
    #                               code=status.HTTP_401_UNAUTHORIZED)

    if upload_id is not None:
        upload = CSVUpload.objects.filter(id=upload_id).first()
        if upload is None:
            raise ValidationException(f"CSV Upload {upload_id} not found", code=status.HTTP_404_NOT_FOUND)

        serializer = CSVUploadSmallSerializer(upload, many=False)
        return Response(serializer.data, status=status.HTTP_200_OK)

    csv = CSVUpload.objects.all()
    serializer = CSVUploadSmallSerializer(csv, many=True)

    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([AllowAny])
def process_github_webhook(request, subscription_token):

    subscription = RepositorySubscription.objects.filter(token=subscription_token).first()
    if subscription is None:
        raise ValidationException(f"Subscription not found with token {subscription_token}")

    if subscription.status == "DISABLED":
        logger.debug("Ignored because subscription has been disabled")
        async_unsubscribe_repo.delayed(subscription.hook_id, force_delete=False)
        return Response("Ignored because subscription has been disabled", status=status.HTTP_200_OK)

    academy_slugs = set([subscription.owner.slug] + [academy.slug for academy in subscription.shared_with.all()])
    payload = request.data.copy()
    payload["scope"] = request.headers["X-GitHub-Event"]

    if "repository" in payload and subscription.repository != payload["repository"]["html_url"]:
        raise ValidationException(
            "Webhook was called from a different repository than its original subscription: "
            + payload["repository"]["html_url"]
        )

    if payload["scope"] == "ping":
        subscription.status = "OPERATIONAL"
        subscription.status_message = "Answered github ping successfully"
        subscription.save()
        return Response("Ready", status=status.HTTP_200_OK)

    subscription.last_call = timezone.now()
    subscription.save()
    for academy_slug in academy_slugs:
        webhook = add_github_webhook(payload, academy_slug)
        if webhook:
            logger.debug("triggering signal github_webhook: " + payload["scope"])
            github_webhook.send_robust(instance=webhook, sender=RepositoryWebhook)
            return Response(payload, status=status.HTTP_200_OK)
        else:
            logger.debug(f"Error at processing github webhook from academy {academy_slug}")
            raise ValidationException(f"Error at processing github webhook from academy {academy_slug}")


@api_view(["POST"])
@permission_classes([AllowAny])
def process_stripe_webhook(request):
    import logging

    logger = logging.getLogger(__name__)

    event = None
    payload = request.body
    sig_header = request.headers.get("Stripe-Signature", None)
    endpoint_secret = get_stripe_webhook_secret(payload)

    try:
        if not sig_header:
            logger.error("No Stripe-Signature header found")
            raise stripe.error.SignatureVerificationError(None, None)

        logger.info("Processing Stripe webhook...")
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
        logger.info(f"Successfully processed event: {event.get('type', 'unknown')}")

    except ValueError as e:
        logger.error(f"Invalid payload: {str(e)}")
        add_stripe_webhook_error(payload, sig_header, slug="invalid-payload", message=str(e))
        raise ValidationException("Invalid payload", code=400, slug="invalid-payload")

    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Webhook signature verification failed: {str(e)}")
        add_stripe_webhook_error(payload, sig_header, slug="not-allowed", message=str(e))
        raise ValidationException("Not allowed", code=403, slug="not-allowed")

    if event := add_stripe_webhook(event):
        logger.info(f"Created StripeEvent with ID: {event.id}")
        logger.info("About to call send_robust...")
        try:
            signals.stripe_webhook.send_robust(event_id=event.id, sender=event.__class__)
            logger.info("Successfully sent stripe_webhook signal")
        except Exception as e:
            logger.error(f"Error in send_robust: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")

        logger.info("Sent stripe_webhook signal")

    logger.info("Webhook processed successfully")
    return Response({"success": True})


class RepositorySubscriptionView(APIView, GenerateLookupsMixin):
    """
    List all snippets, or create a new snippet.
    """

    extensions = APIViewExtensions(sort="-created_at", paginate=True)

    @capable_of("read_asset")
    def get(self, request, academy_id=None):
        handler = self.extensions(request)

        _academy = Academy.objects.get(id=academy_id)
        items = RepositorySubscription.objects.filter(Q(shared_with=_academy) | Q(owner=_academy))
        lookup = {}

        if "repository" in self.request.GET:
            param = self.request.GET.get("repository")
            items = items.filter(repository=param)

        items = items.filter(**lookup)
        items = handler.queryset(items)

        serializer = RepoSubscriptionSmallSerializer(items, many=True)

        return handler.response(serializer.data)

    @capable_of("crud_asset")
    def post(self, request, academy_id=None):
        lang = get_user_language(request)

        serializer = RepositorySubscriptionSerializer(
            data=request.data, context={"request": request, "academy": academy_id, "lang": lang}
        )
        if serializer.is_valid():
            instance = serializer.save()
            return Response(RepoSubscriptionSmallSerializer(instance).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of("crud_asset")
    def put(self, request, academy_id=None, subscription_id=None):
        lang = get_user_language(request)

        subs = RepositorySubscription.objects.filter(id=subscription_id).first()
        if subs is None:
            raise ValidationException(
                translation(
                    lang,
                    en=f"No subscription has been found with id {subscription_id}",
                    es=f"No se ha encontrado una subscripcion con id {subscription_id}",
                    slug="subscription-not-found",
                )
            )

        serializer = RepositorySubscriptionSerializer(
            subs, data=request.data, context={"request": request, "academy": academy_id, "lang": lang}
        )
        if serializer.is_valid():
            instance = serializer.save()
            return Response(RepoSubscriptionSmallSerializer(instance).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AcademyDownloadView(APIView):
    """
    Academy-specific download endpoint with proper capability check
    """

    @capable_of("read_downloads")
    def get(self, request, academy_id=None, download_id=None):
        lang = get_user_language(request)

        if download_id is not None:
            download = CSVDownload.objects.filter(id=download_id, academy__id=academy_id).first()
            if download is None:
                raise ValidationException(
                    translation(
                        lang,
                        en=f"CSV Download {download_id} not found for academy {academy_id}",
                        es=f"Descarga CSV {download_id} no encontrada para la academia {academy_id}",
                        slug="download-not-found",
                    ),
                    code=status.HTTP_404_NOT_FOUND,
                )

            raw = request.GET.get("raw", "")
            if raw == "true":
                from ..services.google_cloud import Storage

                try:
                    storage = Storage()
                    cloud_file = storage.file(os.getenv("DOWNLOADS_BUCKET", None), download.name)
                    buffer = cloud_file.stream_download()

                except CircuitBreakerError:
                    raise ValidationException(
                        translation(
                            lang,
                            en="The circuit breaker is open due to an error, please try again later",
                            es="El circuit breaker está abierto debido a un error, por favor intente más tarde",
                            slug="circuit-breaker-open",
                        ),
                        slug="circuit-breaker-open",
                        data={"service": "Google Cloud Storage"},
                        silent=True,
                        code=503,
                    )

                return StreamingHttpResponse(
                    _async_iter_from_list(buffer.all()),
                    content_type="text/csv",
                    headers={"Content-Disposition": f"attachment; filename={download.name}"},
                )
            else:
                serializer = CSVDownloadSmallSerializer(download, many=False)
                return Response(serializer.data, status=status.HTTP_200_OK)

        # List all downloads for the academy
        csv_downloads = CSVDownload.objects.filter(academy__id=academy_id)
        serializer = CSVDownloadSmallSerializer(csv_downloads, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)


class AcademyDownloadSignedUrlView(APIView):
    """
    Generate signed URLs for CSV downloads with temporary access
    """

    @capable_of("read_downloads")
    def get(self, request, academy_id=None, download_id=None):
        lang = get_user_language(request)

        # Validate download exists and belongs to academy
        download = CSVDownload.objects.filter(id=download_id, academy__id=academy_id, status="DONE").first()
        if download is None:
            raise ValidationException(
                translation(
                    lang,
                    en=f"CSV Download {download_id} not found or not ready for academy {academy_id}",
                    es=f"Descarga CSV {download_id} no encontrada o no lista para la academia {academy_id}",
                    slug="download-not-found-or-not-ready",
                ),
                code=status.HTTP_404_NOT_FOUND,
            )

        # Generate signed URL using Storage helper method
        import os

        from ..services.google_cloud import Storage

        expiration_hours = int(request.GET.get("expiration_hours", 1))

        try:
            storage = Storage()
            signed_url = storage.generate_download_signed_url(
                bucket_name=os.getenv("DOWNLOADS_BUCKET", None),
                file_name=download.name,
                expiration_hours=expiration_hours,
            )

            return Response(
                {
                    "signed_url": signed_url,
                    "expires_in_hours": min(expiration_hours, 24),
                    "filename": download.name,
                    "download_id": download.id,
                },
                status=status.HTTP_200_OK,
            )

        except CircuitBreakerError:
            raise ValidationException(
                translation(
                    lang,
                    en="The circuit breaker is open due to an error, please try again later",
                    es="El circuit breaker está abierto debido a un error, por favor intente más tarde",
                    slug="circuit-breaker-open",
                ),
                slug="circuit-breaker-open",
                data={"service": "Google Cloud Storage"},
                silent=True,
                code=503,
            )
        except Exception as e:
            raise ValidationException(
                translation(
                    lang,
                    en=f"Failed to generate signed URL: {str(e)}",
                    es=f"Error al generar URL firmada: {str(e)}",
                    slug="signed-url-generation-failed",
                ),
                code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AcademyScriptView(APIView):
    """
    API endpoint to trigger and run monitoring scripts via POST.
    Returns MonitorScript serialization with MonitoringErrors created during that run.
    """

    @capable_of("read_asset")
    def post(self, request, academy_id=None, script_slug=None):
        lang = get_user_language(request)

        # Validate academy
        academy = Academy.objects.filter(id=academy_id).first()
        if not academy:
            raise ValidationException(
                translation(
                    lang,
                    en=f"Academy {academy_id} not found",
                    es=f"Academia {academy_id} no encontrada",
                    slug="academy-not-found",
                ),
                code=status.HTTP_404_NOT_FOUND,
            )

        # Find MonitorScript by slug and academy
        script = MonitorScript.objects.filter(
            script_slug=script_slug, application__academy=academy
        ).first()

        if not script:
            raise ValidationException(
                translation(
                    lang,
                    en=f"Monitoring script '{script_slug}' not found for academy {academy_id}",
                    es=f"Script de monitoreo '{script_slug}' no encontrado para la academia {academy_id}",
                    slug="script-not-found",
                ),
                code=status.HTTP_404_NOT_FOUND,
            )

        # Execute the script
        results = run_script(script)

        # Refresh script from database to get updated fields
        script.refresh_from_db()

        # Get the errors created during this run
        monitoring_errors = results.get("monitoring_errors", [])

        # Serialize the script
        script_serializer = MonitorScriptSmallSerializer(script)
        script_data = script_serializer.data
        
        # Serialize the errors
        errors_serializer = MonitoringErrorSerializer(monitoring_errors, many=True)
        
        # Combine script and errors
        response_data = {
            **script_data,
            "monitoring_errors": errors_serializer.data,
        }

        return Response(response_data, status=status.HTTP_200_OK)


class MonitoringReportView(APIView):
    @capable_of("read_monitoring_report")
    def get(self, request, academy_id=None, report_type=None):
        if not report_type:
            metadata = get_report_type_metadata()
            return Response(metadata, status=status.HTTP_200_OK)

        lang = get_user_language(request)
        queryset, config = _get_filtered_report_queryset(request, report_type, academy_id, lang)

        handler = APIViewExtensions(sort=config.default_sort, paginate=True)(request)
        queryset = handler.queryset(queryset)

        serializer = config.list_serializer(queryset, many=True)
        return handler.response(serializer.data)


class MonitoringReportDetailView(APIView):
    @capable_of("read_monitoring_report")
    def get(self, request, report_type=None, report_id=None, academy_id=None):
        lang = get_user_language(request)
        config = _get_report_api_config_or_404(report_type, lang)

        if not config.supports_detail:
            raise ValidationException(
                translation(
                    lang,
                    en=f"Report {report_type} does not support detail view",
                    es=f"El reporte {report_type} no soporta vista de detalle",
                    slug="report-detail-not-supported",
                ),
                code=status.HTTP_404_NOT_FOUND,
            )

        instance = config.model.objects.filter(id=report_id, academy_id=academy_id).first()
        if instance is None:
            raise ValidationException(
                translation(
                    lang,
                    en=f"Report record {report_id} not found",
                    es=f"Registro de reporte {report_id} no encontrado",
                    slug="report-record-not-found",
                ),
                code=status.HTTP_404_NOT_FOUND,
            )

        serializer = config.detail_serializer(instance, many=False)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MonitoringReportSummaryView(APIView):
    @capable_of("read_monitoring_report")
    def get(self, request, report_type=None, academy_id=None):
        lang = get_user_language(request)
        queryset, config = _get_filtered_report_queryset(request, report_type, academy_id, lang)

        if config.supports_summary is False or config.summary_builder is None:
            raise ValidationException(
                translation(
                    lang,
                    en=f"Report {report_type} does not support summary view",
                    es=f"El reporte {report_type} no soporta vista de resumen",
                    slug="report-summary-not-supported",
                ),
                code=status.HTTP_404_NOT_FOUND,
            )

        payload = config.summary_builder(queryset, academy_id)
        return Response(payload, status=status.HTTP_200_OK)


def _job_fingerprint(report_type: str, academy_id: int, date_start: date, date_end: date, params: dict) -> str:
    payload = {
        "report_type": report_type,
        "academy_id": academy_id,
        "date_start": date_start.isoformat(),
        "date_end": date_end.isoformat(),
        "params": params,
    }
    return sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


class MonitoringReportGenerationView(APIView):
    @capable_of("read_monitoring_report")
    def post(self, request, report_type=None, academy_id=None):
        lang = get_user_language(request)
        data = {**request.data, "report_type": report_type}
        serializer = ReportGenerationTriggerSerializer(data=data, context={"lang": lang, "academy_id": academy_id})
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        params = {}
        for key in ["date", "date_start", "date_end", "days_back"]:
            if key in request.data:
                params[key] = request.data.get(key)

        fingerprint = _job_fingerprint(
            report_type=payload["report_type"],
            academy_id=academy_id,
            date_start=payload["date_start"],
            date_end=payload["date_end"],
            params=params,
        )

        if not payload.get("force", False):
            existing = ReportGenerationJob.objects.filter(
                academy_id=academy_id,
                report_type=payload["report_type"],
                fingerprint=fingerprint,
                status__in=[ReportGenerationJob.Status.PENDING, ReportGenerationJob.Status.RUNNING],
            ).first()
            if existing:
                return Response(ReportGenerationJobSerializer(existing, many=False).data, status=status.HTTP_200_OK)

        job = ReportGenerationJob.objects.create(
            report_type=payload["report_type"],
            status=ReportGenerationJob.Status.PENDING,
            status_message="Queued",
            academy_id=academy_id,
            requested_by=request.user,
            date_start=payload["date_start"],
            date_end=payload["date_end"],
            params=params,
            fingerprint=fingerprint,
        )

        task_result = generate_report_job.delay(job.id)
        job.celery_task_id = task_result.id
        job.save(update_fields=["celery_task_id", "updated_at"])

        return Response(ReportGenerationJobSerializer(job, many=False).data, status=status.HTTP_202_ACCEPTED)


class MonitoringReportGenerationDetailView(APIView):
    @capable_of("read_monitoring_report")
    def get(self, request, report_type=None, job_id=None, academy_id=None):
        lang = get_user_language(request)
        job = ReportGenerationJob.objects.filter(id=job_id, academy_id=academy_id, report_type=report_type).first()
        if not job:
            raise ValidationException(
                translation(
                    lang,
                    en=f"Report generation job {job_id} not found",
                    es=f"Trabajo de generación de reporte {job_id} no encontrado",
                    slug="report-generation-job-not-found",
                ),
                code=status.HTTP_404_NOT_FOUND,
            )

        return Response(ReportGenerationJobSerializer(job, many=False).data, status=status.HTTP_200_OK)


class MonitoringReportGenerationListView(APIView):
    @capable_of("read_monitoring_report")
    def get(self, request, academy_id=None):
        lang = get_user_language(request)
        queryset = ReportGenerationJob.objects.filter(academy_id=academy_id).order_by("-created_at")

        status_filter = request.GET.get("status")
        if status_filter:
            statuses = [x.strip().upper() for x in status_filter.split(",") if x.strip()]
            allowed = {x[0] for x in ReportGenerationJob.Status.choices}
            unexpected = [x for x in statuses if x not in allowed]
            if unexpected:
                raise ValidationException(
                    translation(
                        lang,
                        en=f"Invalid status filter: {', '.join(unexpected)}",
                        es=f"Filtro status inválido: {', '.join(unexpected)}",
                        slug="invalid-status-filter",
                    )
                )
            queryset = queryset.filter(status__in=statuses)

        report_type = request.GET.get("report_type")
        if report_type:
            allowed = {x[0] for x in ReportGenerationJob.ReportType.choices}
            if report_type not in allowed:
                raise ValidationException(
                    translation(
                        lang,
                        en=f"Invalid report_type filter: {report_type}",
                        es=f"Filtro report_type inválido: {report_type}",
                        slug="invalid-report-type-filter",
                    )
                )
            queryset = queryset.filter(report_type=report_type)

        handler = APIViewExtensions(sort="-created_at", paginate=True)(request)
        queryset = handler.queryset(queryset)
        serialized = ReportGenerationJobListSerializer(queryset, many=True).data
        return handler.response(serialized)
