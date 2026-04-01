import hashlib
import math
import os
from datetime import date, datetime
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import pandas as pd
from capyc.core.i18n import translation
from capyc.rest_framework.exceptions import ValidationException
from circuitbreaker import CircuitBreakerError
from dateutil.relativedelta import relativedelta
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from rest_framework import status
from rest_framework.parsers import FileUploadParser, MultiPartParser
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_csv.renderers import CSVRenderer

from breathecode.admissions.models import Academy, Cohort, CohortUser
from breathecode.authenticate.actions import get_user_language
from breathecode.authenticate.models import ProfileAcademy
from breathecode.payments.models import Consumable
from breathecode.notify.actions import get_template_content
from breathecode.provisioning import tasks
from breathecode.provisioning.serializers import (
    AcademyVPSCreateSerializer,
    AcademyVPSListSerializer,
    GetProvisioningAcademySerializer,
    GetProvisioningBillDetailSerializer,
    GetProvisioningBillSmallSerializer,
    GetProvisioningProfile,
    GetProvisioningUserConsumptionDetailSerializer,
    GetProvisioningUserConsumptionSerializer,
    GetProvisioningVendorSerializer,
    ProvisioningAcademyCreateSerializer,
    ProvisioningAcademyUpdateSerializer,
    resolve_allowed_machine_types_for_vendor,
    ProvisioningBillHTMLSerializer,
    ProvisioningBillSerializer,
    ProvisioningProfileCreateUpdateSerializer,
    ProvisioningUserConsumptionHTMLResumeSerializer,
    VPSDetailSerializer,
    VPSListSerializer,
    VPSRequestSerializer,
    validate_vendor_settings,
)
from breathecode.utils import capable_of, cut_csv
from breathecode.utils.api_view_extensions.api_view_extensions import APIViewExtensions
from breathecode.utils.decorators import has_permission
from breathecode.utils.io.file import count_csv_rows
from breathecode.utils.views import private_view, render_message

from .actions import (
    get_provisioning_vendor,
    request_vps,
    resolve_llm_client_and_external_id,
    resolve_provisioning_academy_for_llm,
    get_eligible_academy_and_vendor_for_vps,
    get_vps_provisioning_academy_for_academy,
    request_vps_for_student,
)
from .models import (
    BILL_STATUS,
    ProvisioningAcademy,
    ProvisioningBill,
    ProvisioningLLM,
    ProvisioningProfile,
    ProvisioningUserConsumption,
    ProvisioningVPS,
    ProvisioningVendor,
)
from .utils.coding_editor_client import CodingEditorConnectionError, get_coding_editor_client
from .utils.llm_client import LLMClientError, LLMConnectionError, get_llm_client
from .utils.vps_client import VPSProvisioningError, get_vps_client

_VALID_VENDOR_TYPE_VALUES = frozenset(c.value for c in ProvisioningVendor.VendorType)


def _optional_vendor_type_from_query(request, *, lang: str) -> str | None:
    """Parse optional ``vendor_type`` query string; raise ValidationException if invalid."""
    raw = request.GET.get("vendor_type")
    if raw is None:
        return None
    if isinstance(raw, str) and not raw.strip():
        return None
    normalized = raw.strip().upper()
    if normalized not in _VALID_VENDOR_TYPE_VALUES:
        allowed = ", ".join(sorted(_VALID_VENDOR_TYPE_VALUES))
        raise ValidationException(
            translation(
                lang,
                en=f"Invalid vendor_type. Must be one of: {allowed}.",
                es=f"vendor_type no válido. Debe ser uno de: {allowed}.",
                slug="invalid-provisioning-vendor-type",
            ),
            code=400,
        )
    return normalized


def _normalize_allowed_values(settings, key, cast):
    values = settings.get(key) or []
    normalized = []
    for value in values:
        try:
            normalized.append(cast(value))
        except (TypeError, ValueError):
            continue
    return set(normalized)


def _build_vendor_selection(vendor_name, vendor_settings, request_data, lang):
    slug = (vendor_name or "").lower().strip()
    if slug == "digitalocean":
        return _build_digitalocean_vendor_selection(vendor_settings, request_data, lang)
    if slug != "hostinger":
        return {}

    vendor_selection = request_data.get("vendor_selection") or {}
    selected_item = (vendor_selection.get("item_id") or "").strip() or None
    selected_template = vendor_selection.get("template_id")
    selected_data_center = vendor_selection.get("data_center_id")
    allowed_items = _normalize_allowed_values(vendor_settings, "item_ids", lambda value: str(value).strip())
    allowed_templates = _normalize_allowed_values(vendor_settings, "template_ids", int)
    allowed_data_centers = _normalize_allowed_values(vendor_settings, "data_center_ids", int)

    # Do not allow the vendor client to "guess" defaults. We require explicit
    # allowlists to be configured before provisioning starts.
    if not allowed_items or not allowed_templates or not allowed_data_centers:
        raise ValidationException(
            translation(
                lang,
                en="Hostinger vendor allowlists are not configured for this academy. Please set item_ids, template_ids, and data_center_ids first.",
                es="Las allowlists de Hostinger no estan configuradas para esta academia. Primero configura item_ids, template_ids y data_center_ids.",
                slug="hostinger-vendor-allowlists-missing",
            ),
            code=400,
        )

    if not selected_item and len(allowed_items) == 1:
        selected_item = next(iter(allowed_items))
    if selected_template is None and len(allowed_templates) == 1:
        selected_template = next(iter(allowed_templates))
    if selected_data_center is None and len(allowed_data_centers) == 1:
        selected_data_center = next(iter(allowed_data_centers))

    if not selected_item:
        raise ValidationException(
            translation(
                lang,
                en="item_id is required (must be one of the configured item_ids).",
                es="Se requiere item_id (debe estar dentro de los item_ids configurados).",
                slug="invalid-vps-item-id-required",
            ),
            code=400,
        )
    if selected_template is None:
        raise ValidationException(
            translation(
                lang,
                en="template_id is required (must be one of the configured template_ids).",
                es="Se requiere template_id (debe estar dentro de los template_ids configurados).",
                slug="invalid-vps-template-id-required",
            ),
            code=400,
        )
    if selected_data_center is None:
        raise ValidationException(
            translation(
                lang,
                en="data_center_id is required (must be one of the configured data_center_ids).",
                es="Se requiere data_center_id (debe estar dentro de los data_center_ids configurados).",
                slug="invalid-vps-data-center-id-required",
            ),
            code=400,
        )

    if selected_item and selected_item not in allowed_items:
        raise ValidationException(
            translation(
                lang,
                en="Selected item_id is not allowed for this academy.",
                es="El item_id seleccionado no esta permitido para esta academia.",
                slug="invalid-vps-item-id",
            ),
            code=400,
        )
    if selected_template is not None and int(selected_template) not in allowed_templates:
        raise ValidationException(
            translation(
                lang,
                en="Selected template_id is not allowed for this academy.",
                es="El template_id seleccionado no esta permitido para esta academia.",
                slug="invalid-vps-template-id",
            ),
            code=400,
        )
    if selected_data_center is not None and int(selected_data_center) not in allowed_data_centers:
        raise ValidationException(
            translation(
                lang,
                en="Selected data_center_id is not allowed for this academy.",
                es="El data_center_id seleccionado no esta permitido para esta academia.",
                slug="invalid-vps-data-center-id",
            ),
            code=400,
        )

    payload = {}
    payload["item_id"] = selected_item
    payload["template_id"] = int(selected_template)
    payload["data_center_id"] = int(selected_data_center)
    return payload


def _build_digitalocean_vendor_selection(vendor_settings, request_data, lang):
    vendor_selection = request_data.get("vendor_selection") or {}
    selected_region = (vendor_selection.get("region_slug") or "").strip() or None
    selected_size = (vendor_selection.get("size_slug") or "").strip() or None
    selected_image = (vendor_selection.get("image_slug") or "").strip() or None
    allowed_regions = _normalize_allowed_values(vendor_settings, "region_slugs", lambda value: str(value).strip())
    allowed_sizes = _normalize_allowed_values(vendor_settings, "size_slugs", lambda value: str(value).strip())
    allowed_images = _normalize_allowed_values(vendor_settings, "image_slugs", lambda value: str(value).strip())

    if not allowed_regions or not allowed_sizes or not allowed_images:
        raise ValidationException(
            translation(
                lang,
                en="DigitalOcean vendor allowlists are not configured for this academy. Please set region_slugs, size_slugs, and image_slugs first.",
                es="Las allowlists de DigitalOcean no estan configuradas para esta academia. Primero configura region_slugs, size_slugs y image_slugs.",
                slug="digitalocean-vendor-allowlists-missing",
            ),
            code=400,
        )

    if not selected_region and len(allowed_regions) == 1:
        selected_region = next(iter(allowed_regions))
    if not selected_size and len(allowed_sizes) == 1:
        selected_size = next(iter(allowed_sizes))
    if not selected_image and len(allowed_images) == 1:
        selected_image = next(iter(allowed_images))

    if not selected_region:
        raise ValidationException(
            translation(
                lang,
                en="region_slug is required (must be one of the configured region_slugs).",
                es="Se requiere region_slug (debe estar dentro de los region_slugs configurados).",
                slug="invalid-vps-region-slug-required",
            ),
            code=400,
        )
    if not selected_size:
        raise ValidationException(
            translation(
                lang,
                en="size_slug is required (must be one of the configured size_slugs).",
                es="Se requiere size_slug (debe estar dentro de los size_slugs configurados).",
                slug="invalid-vps-size-slug-required",
            ),
            code=400,
        )
    if not selected_image:
        raise ValidationException(
            translation(
                lang,
                en="image_slug is required (must be one of the configured image_slugs).",
                es="Se requiere image_slug (debe estar dentro de los image_slugs configurados).",
                slug="invalid-vps-image-slug-required",
            ),
            code=400,
        )

    if selected_region not in allowed_regions:
        raise ValidationException(
            translation(
                lang,
                en="Selected region_slug is not allowed for this academy.",
                es="El region_slug seleccionado no esta permitido para esta academia.",
                slug="invalid-vps-region-slug",
            ),
            code=400,
        )
    if selected_size not in allowed_sizes:
        raise ValidationException(
            translation(
                lang,
                en="Selected size_slug is not allowed for this academy.",
                es="El size_slug seleccionado no esta permitido para esta academia.",
                slug="invalid-vps-size-slug",
            ),
            code=400,
        )
    if selected_image not in allowed_images:
        raise ValidationException(
            translation(
                lang,
                en="Selected image_slug is not allowed for this academy.",
                es="El image_slug seleccionado no esta permitido para esta academia.",
                slug="invalid-vps-image-slug",
            ),
            code=400,
        )

    return {
        "region_slug": selected_region,
        "size_slug": selected_size,
        "image_slug": selected_image,
    }


def _get_hostinger_vendor_options(token: str, lang: str):
    import hostinger_api
    from hostinger_api.rest import ApiException

    configuration = hostinger_api.Configuration(access_token=token)
    with hostinger_api.ApiClient(configuration) as api_client:
        try:
            dc_api = hostinger_api.VPSDataCentersApi(api_client)
            template_api = hostinger_api.VPSOSTemplatesApi(api_client)
            catalog_api = hostinger_api.BillingCatalogApi(api_client)
            dc_response = dc_api.get_data_center_list_v1()
            template_response = template_api.get_templates_v1()
            catalog_response = catalog_api.get_catalog_item_list_v1(category="VPS")
        except ApiException as e:
            raise ValidationException(
                translation(
                    lang,
                    en=f"Cannot fetch Hostinger options: {e}",
                    es=f"No se pudieron obtener las opciones de Hostinger: {e}",
                    slug="hostinger-options-fetch-failed",
                ),
                code=400,
            )

    # Hostinger SDK returns plain lists for these endpoints.
    data_centers = dc_response if isinstance(dc_response, list) else []
    templates = template_response if isinstance(template_response, list) else []
    catalog_items = catalog_response if isinstance(catalog_response, list) else []

    def _serialize_hostinger_item(item):
        if hasattr(item, "model_dump"):
            return item.model_dump()
        if hasattr(item, "to_dict"):
            return item.to_dict()
        if isinstance(item, dict):
            return item
        if hasattr(item, "__dict__"):
            return {k: v for k, v in item.__dict__.items() if not k.startswith("_")}
        return item

    return {
        "data_centers": [_serialize_hostinger_item(x) for x in data_centers],
        "templates": [_serialize_hostinger_item(x) for x in templates],
        "catalog_items": [_serialize_hostinger_item(x) for x in catalog_items],
    }


def _get_digitalocean_vendor_options(token: str, lang: str):
    from breathecode.provisioning.utils.vps_client import VPSProvisioningError
    from breathecode.services.digitalocean.client import fetch_vendor_options

    try:
        return fetch_vendor_options(token)
    except VPSProvisioningError as e:
        raise ValidationException(
            translation(
                lang,
                en=f"Cannot fetch DigitalOcean options: {e}",
                es=f"No se pudieron obtener las opciones de DigitalOcean: {e}",
                slug="digitalocean-options-fetch-failed",
            ),
            code=400,
        )


@private_view()
def redirect_new_container(request, token):

    user = token.user
    cohort_id = request.GET.get("cohort", None)
    if cohort_id is None or cohort_id in ["", "undefined"]:
        return render_message(request, "Please specificy a cohort in the URL")

    url = request.GET.get("repo", None)
    if url is None:
        cohort = Cohort.objects.filter(id=cohort_id).first()
        academy = None
        if cohort:
            academy = cohort.academy

        return render_message(request, "Please specify a repository in the URL", academy=academy)

    cu = CohortUser.objects.filter(user=user, cohort_id=cohort_id).first()
    if cu is None:
        cohort = Cohort.objects.filter(id=cohort_id).first()
        academy = None
        if cohort:
            academy = cohort.academy

        return render_message(request, f"You don't seem to belong to this cohort {cohort_id}.", academy=academy)

    academy_id = cu.cohort.academy.id
    pa = ProfileAcademy.objects.filter(user=user, academy__id=academy_id).first()
    if pa is None:
        obj = {}
        if cu.cohort.academy:
            obj["COMPANY_INFO_EMAIL"] = cu.cohort.academy.feedback_email

        return render_message(
            request, f"You don't seem to belong to academy {cu.cohort.academy.name}", academy=cu.cohort.academy
        )

    vendor = None
    try:
        vendor = get_provisioning_vendor(user, pa, cu.cohort)
    except Exception as e:
        return render_message(request, str(e), academy=cu.cohort.academy)

    if vendor.name.lower() == "gitpod":
        return redirect(f"https://gitpod.io/#{url}")
    if vendor.name.lower() == "codespaces":
        url = url.replace("https://github.com/", "")
        return redirect(f"https://github.com/codespaces/new/?repo={url}")

    return render_message(
        request,
        f"Unknown provisioning vendor: '{vendor.name}', please speak with your program manager.",
        academy=cu.cohort.academy,
    )


def redirect_new_container_public(request):

    from breathecode.registry.models import Asset

    # user = token.user

    lang = request.GET.get("lang", None)
    repo = request.GET.get("repo", None)
    if repo is None:
        return render_message(request, "Please specify a repository in the URL")

    urls = {"gitpod": "https://gitpod.io/#", "codespaces": "https://github.com/codespaces/new/?repo="}
    url_modifiers = {"codespaces": lambda x: x.replace("https://github.com/", "")}
    vendors = request.GET.get("vendor", "codespaces,gitpod").split(",")
    buttons = []

    asset = Asset.objects.filter(readme_url__icontains=repo)
    if lang is not None:
        asset = asset.filter(lang=lang)
    asset = asset.first()
    if asset and asset.learnpack_deploy_url:
        buttons.append(
            {
                "label": "Start tutorial",
                "url": asset.learnpack_deploy_url,
                "icon": "/static/img/learnpack.svg",
            }
        )

    else:
        for v in vendors:
            if v not in urls:
                return render_message(request, f"Invalid provisioning vendor: {v}")

            _url = urls[v] + repo
            if v in url_modifiers:
                _url = urls[v] + url_modifiers[v](repo)

            buttons.append(
                {
                    "label": f"Open in {v.capitalize()}",
                    "url": _url,
                    "icon": f"/static/img/{v}.svg",
                }
            )

    data = {
        # 'title': item.academy.name,
        "buttons": buttons,
        # 'COMPANY_INFO_EMAIL': item.academy.feedback_email,
    }
    template = get_template_content("choose_vendor", data)
    return HttpResponse(template["html"])


@private_view()
def redirect_workspaces(request, token):

    user = token.user
    cohort_id = request.GET.get("cohort", None)
    if cohort_id is None:
        return render_message(request, "Please specificy a cohort in the URL")

    url = request.GET.get("repo", None)
    if url is None:
        cohort = Cohort.objects.filter(id=cohort_id).first()
        academy = None
        if cohort:
            academy = cohort.academy

        return render_message(request, 'Please specificy a repository "repo" in the URL', academy=academy)

    cu = CohortUser.objects.filter(user=user, cohort_id=cohort_id).first()
    if cu is None:
        cohort = Cohort.objects.filter(id=cohort_id).first()
        academy = None
        if cohort:
            academy = cohort.academy

        return render_message(request, f"You don't seem to belong to this cohort {cohort_id}.", academy=academy)

    academy_id = cu.cohort.academy.id
    pa = ProfileAcademy.objects.filter(user=user, academy__id=academy_id).first()
    if pa is None:
        return render_message(
            request, f"You don't seem to belong to academy {cu.cohort.academy.name}", academy=cu.cohort.academy
        )

    vendor = None
    try:
        vendor = get_provisioning_vendor(user, pa, cu.cohort)

    except Exception as e:
        return render_message(request, str(e), academy=cu.cohort.academy)

    return redirect(vendor.workspaces_url)


class AcademyProvisioningUserConsumptionView(APIView):
    extensions = APIViewExtensions(sort="-id")

    renderer_classes = [JSONRenderer, CSVRenderer]

    @capable_of("read_provisioning_activity")
    def get(self, request, academy_id=None):
        handler = self.extensions(request)
        lang = get_user_language(request)

        query = handler.lookup.build(
            lang,
            strings={
                "iexact": [
                    "hash",
                    "username",
                    "status",
                    "kind__product_name",
                    "kind__sku",
                ],
            },
            datetimes={
                "gte": ["processed_at"],
                "lte": ["created_at"],  # fix it
            },
            overwrite={
                "start": "processed_at",
                "end": "created_at",
                "product_name": "kind__product_name",
                "sku": "kind__sku",
            },
        )

        items = ProvisioningUserConsumption.objects.filter(query, bills__academy__id=academy_id)
        items = handler.queryset(items)

        serializer = GetProvisioningUserConsumptionSerializer(items, many=True)
        return Response(serializer.data)


class UploadView(APIView):
    """
    put:
        Upload a file to Google Cloud.
    """

    parser_classes = [MultiPartParser, FileUploadParser]

    # permission_classes = [AllowAny]

    # upload was separated because in one moment I think that the serializer
    # not should get many create and update operations together
    def upload(self, lang, file):
        from ..services.google_cloud import Storage

        # files validation below
        if file.content_type != "text/csv":
            raise ValidationException(
                translation(
                    lang,
                    en="You can upload only files on the following formats: application/csv",
                    es="Solo puedes subir archivos en los siguientes formatos: application/csv",
                    slug="bad-format",
                )
            )

        content_bytes = file.read()
        hash = hashlib.sha256(content_bytes).hexdigest()

        file.seek(0)
        csv_first_line = cut_csv(file, first=1)
        df = pd.read_csv(csv_first_line, sep=",")
        df.reset_index()

        format_error = True

        # gitpod
        fields = ["id", "credits", "startTime", "endTime", "kind", "userName", "contextURL"]
        if len(df.keys().intersection(fields)) == len(fields):
            format_error = False

            csv_last_line = cut_csv(file, last=1)
            df2 = pd.read_csv(csv_last_line, sep=",", usecols=fields)
            df2.reset_index()

            try:

                first = df2["startTime"][0].split("-")
                last = df["startTime"][0].split("-")

                first[2] = first[2].split("T")[0]
                last[2] = last[2].split("T")[0]

                first = date(int(first[0]), int(first[1]), int(first[2]))
                last = date(int(last[0]), int(last[1]), int(last[2]))

            except Exception:
                raise ValidationException(
                    translation(
                        lang,
                        en="CSV file from unknown source",
                        es="Archivo CSV de fuente desconocida",
                        slug="bad-date-format",
                    )
                )

            delta = relativedelta(last, first)

            if delta.years > 0 or delta.months > 1 or (delta.months > 1 and delta.days > 1):
                raise ValidationException(
                    translation(
                        lang,
                        en="Each file must have only one month of data",
                        es="Cada archivo debe tener solo un mes de datos",
                        slug="overflow",
                    )
                )

        if format_error:
            # codespaces
            fields = [
                "username",
                "date",
                "product",
                "sku",
                "quantity",
                "unit_type",
                "applied_cost_per_quantity",
            ]

        if format_error and len(df.keys().intersection(fields)) == len(fields):
            format_error = False

            csv_last_line = cut_csv(file, last=1)
            df2 = pd.read_csv(csv_last_line, sep=",", usecols=fields)
            df2.reset_index()

            try:
                first = df2["date"][0].split("-")
                last = df2["date"][0].split("-")

                # Handle both formats: "2025-02-01T00:00:00.0000000Z" and "2025-03-01"
                if "T" in first[2]:
                    first[2] = first[2].split("T")[0]
                if "T" in last[2]:
                    last[2] = last[2].split("T")[0]

                first = date(int(first[0]), int(first[1]), int(first[2]))
                last = date(int(last[0]), int(last[1]), int(last[2]))

            except Exception:
                raise ValidationException(
                    translation(
                        lang,
                        en="CSV file from unknown source",
                        es="Archivo CSV de fuente desconocida",
                        slug="bad-date-format",
                    )
                )

            delta = relativedelta(last, first)

            if delta.years > 0 or delta.months > 1 or (delta.months > 1 and delta.days > 1):
                raise ValidationException(
                    translation(
                        lang,
                        en="Each file must have only one month of data",
                        es="Cada archivo debe tener solo un mes de datos",
                        slug="overflow",
                    )
                )

        if format_error:
            # rigobot
            fields = [
                "organization",
                "consumption_period_id",
                "consumption_period_start",
                "consumption_period_end",
                "billing_status",
                "total_spent_period",
                "consumption_item_id",
                "user_id",
                "email",
                "consumption_type",
                "pricing_type",
                "total_spent",
                "total_tokens",
                "model",
                "purpose_id",
                "purpose_slug",
                "purpose",
                "created_at",
                "github_username",
            ]

        if format_error and len(df.keys().intersection(fields)) == len(fields):
            format_error = False

            try:
                first = datetime.fromisoformat(df["consumption_period_start"].min())
                last = datetime.fromisoformat(df["consumption_period_end"].max())

            except Exception:
                raise ValidationException(
                    translation(
                        lang,
                        en="CSV file from unknown source",
                        es="Archivo CSV de fuente desconocida",
                        slug="bad-date-format",
                    )
                )

            delta = relativedelta(last, first)

            if delta.years > 0 or delta.months > 1 or (delta.months > 1 and delta.days > 1):
                raise ValidationException(
                    translation(
                        lang,
                        en="Each file must have only one month of data",
                        es="Cada archivo debe tener solo un mes de datos",
                        slug="overflow",
                    )
                )

        # Think about uploading correct files and leaving out incorrect ones
        if format_error:
            raise ValidationException(
                translation(
                    lang,
                    en="CSV file from unknown source or the format has changed and this code must be updated",
                    es="Archivo CSV de fuente desconocida o el formato ha cambiado y este código debe ser "
                    "actualizado",
                    slug="csv-from-unknown-source",
                )
            )

        # upload file section
        try:
            storage = Storage()
            cloud_file = storage.file(os.getenv("PROVISIONING_BUCKET", None), hash)
            created = not cloud_file.exists()
            if created:
                cloud_file.upload(file, content_type=file.content_type)

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

        tasks.upload.delay(hash, total_pages=math.ceil(count_csv_rows(file) / tasks.PANDAS_ROWS_LIMIT))

        data = {"file_name": hash, "status": "PENDING", "created": created}

        return data

    @has_permission("upload_provisioning_activity")
    def put(self, request, academy_id=None):
        files = request.data.getlist("file")
        lang = get_user_language(request)

        created = []
        updated = []
        errors = {}

        result = {
            "success": [],
            "failure": [],
        }

        for i in range(len(files)):
            file = files[i]

            try:
                data = self.upload(lang, file)
                was_created = data.pop("created")

                serialized = {
                    "pk": data["file_name"],
                    "display_field": "index",
                    "display_value": i + 1,
                }

                if was_created:
                    created.append(serialized)
                else:
                    updated.append(serialized)
            except ValidationException as e:
                key = (e.status_code, e.detail)
                if key not in errors:
                    errors[key] = []

                errors[key].append(
                    {
                        "display_field": "index",
                        "display_value": i + 1,
                    }
                )

        if created:
            result["success"].append({"status_code": 201, "resources": created})

        if updated:
            result["success"].append({"status_code": 200, "resources": updated})

        if errors:
            for (status_code, detail), value in errors.items():
                result["failure"].append(
                    {
                        "status_code": status_code,
                        "detail": detail,
                        "resources": value,
                    }
                )

        return Response(result, status=status.HTTP_207_MULTI_STATUS)


@private_view()
def render_html_all_bills(request, token):
    lang = get_user_language(request)
    academy_ids = {
        x.academy.id
        for x in ProfileAcademy.objects.filter(user=request.user, role__capabilities__slug="read_provisioning_bill")
    }

    if not academy_ids:
        return render(
            request,
            "message.html",
            {
                "MESSAGE": translation(
                    lang,
                    en="You don't have the capabilities to read provisioning bills in this academy",
                    es="No tienes capacidads para leer provisioning bills en esta academia",
                    slug="no-access",
                )
            },
            status=403,
        )

    status_mapper = {}
    for key, value in BILL_STATUS:
        status_mapper[key] = value

    lookup = {}

    status = "DUE"
    if "status" in request.GET:
        status = request.GET.get("status")
    lookup["status"] = status.upper()

    if "academy" in request.GET:
        ids = {int(x) for x in request.GET.get("academy").split(",")}
        lookup["academy__id__in"] = academy_ids.intersection(ids)

    else:
        lookup["academy__id__in"] = academy_ids

    items = ProvisioningBill.objects.filter(**lookup).exclude(academy__isnull=True)

    total_price = 0
    for bill in []:
        total_price += bill["total_price"]

    data = {
        "status": status,
        "token": token.key,
        "title": f"Payments {status_mapper[status]}",
        "possible_status": [(key, status_mapper[key]) for key, label in BILL_STATUS],
        "bills": items,
        "total_price": total_price,
    }
    template = get_template_content("provisioning_bills", data)
    return HttpResponse(template["html"])


LIMIT_PER_PAGE_HTML = 10


@private_view()
def render_html_bill(request, token, id=None):
    lang = get_user_language(request)
    academy_ids = {
        x.academy.id
        for x in ProfileAcademy.objects.filter(user=request.user, role__capabilities__slug="crud_provisioning_bill")
    }

    if not academy_ids:
        return render(
            request,
            "message.html",
            {
                "MESSAGE": translation(
                    lang,
                    en="You have no access to this resource",
                    es="No tienes acceso a este recurso",
                    slug="no-access",
                )
            },
            status=403,
        )

    item = ProvisioningBill.objects.filter(id=id, academy__isnull=False).first()

    if item is None:
        obj = {}
        if item.academy:
            obj["COMPANY_INFO_EMAIL"] = item.academy.feedback_email
            obj["COMPANY_LEGAL_NAME"] = item.academy.legal_name or item.academy.name
            obj["COMPANY_LOGO"] = item.academy.logo_url
            obj["COMPANY_NAME"] = item.academy.name

            if "heading" not in obj:
                obj["heading"] = item.academy.name

        return render(
            request,
            "message.html",
            {
                "MESSAGE": translation(
                    lang,
                    en="Bill not found",
                    es="Factura no encontrada",
                    slug="bill-not-found",
                    **obj,
                )
            },
        )

    status_map = {"DUE": "UNDER_REVIEW", "APPROVED": "READY_TO_PAY", "PAID": "ALREADY PAID", "PENDING": "PENDING"}
    status_mapper = {}
    for key, value in BILL_STATUS:
        status_mapper[key] = value

    bill_serialized = ProvisioningBillHTMLSerializer(item, many=False).data

    consumptions = ProvisioningUserConsumption.objects.filter(bills=item)
    pages = math.ceil(consumptions.count() / LIMIT_PER_PAGE_HTML)
    page = int(request.GET.get("page", 0))

    consumptions = consumptions.order_by("username")[0 : (page * LIMIT_PER_PAGE_HTML) + LIMIT_PER_PAGE_HTML]

    consumptions_serialized = ProvisioningUserConsumptionHTMLResumeSerializer(consumptions, many=True).data

    url = request.get_full_path()

    u = urlparse(url)
    query = parse_qs(u.query, keep_blank_values=True)
    query.pop("page", None)
    u = u._replace(query=urlencode(query, True))

    url = urlunparse(u)

    if not "?" in url:
        url += "?"

    page += 1

    data = {
        "bill": bill_serialized,
        "consumptions": consumptions_serialized,
        "status": status_map[item.status],
        "title": item.academy.name,
        "pages": pages,
        "page": page,
        "url": url,
        "COMPANY_INFO_EMAIL": item.academy.feedback_email,
    }
    template = get_template_content("provisioning_invoice", data, academy=item.academy)
    return HttpResponse(template["html"])


class AcademyBillView(APIView):
    """
    List all snippets, or create a new snippet.
    """

    extensions = APIViewExtensions(paginate=True)

    @capable_of("read_provisioning_bill")
    def get(self, request, academy_id=None, bill_id=None):
        handler = self.extensions(request)

        if bill_id is not None:
            bill = ProvisioningBill.objects.filter(academy__id=academy_id, id=bill_id).first()

            if bill is None:
                raise ValidationException("Provisioning Bill not found", code=404, slug="provisioning_bill-not-found")

            serializer = GetProvisioningBillDetailSerializer(bill, many=False)
            return Response(serializer.data)

        items = ProvisioningBill.objects.filter(academy__id=academy_id)

        status = request.GET.get("status", None)
        if status is not None:
            items = items.filter(status__in=status.upper().split(","))

        items = items.order_by(request.GET.get("sort", "-created_at"))

        items = handler.queryset(items)
        serializer = GetProvisioningBillSmallSerializer(items, many=True)

        return handler.response(serializer.data)

    @capable_of("crud_provisioning_bill")
    def put(self, request, bill_id=None, academy_id=None):
        lang = get_user_language(request)

        item = ProvisioningBill.objects.filter(id=bill_id, academy__id=academy_id).first()
        if item is None:
            raise ValidationException(
                translation(
                    lang,
                    en="Not found",
                    es="No encontrado",
                    slug="not-found",
                ),
                code=404,
            )

        serializer = ProvisioningBillSerializer(item, data=request.data, many=False, context={"lang": lang})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AcademyBillConsumptionsView(APIView):
    """
    Get paginated consumptions for a specific bill.
    """

    extensions = APIViewExtensions(paginate=True)

    @capable_of("read_provisioning_bill")
    def get(self, request, academy_id=None, bill_id=None):
        handler = self.extensions(request)

        if bill_id is None:
            raise ValidationException("bill_id is required", code=400, slug="bill-id-required")

        bill = ProvisioningBill.objects.filter(academy__id=academy_id, id=bill_id).first()

        if bill is None:
            raise ValidationException("Provisioning Bill not found", code=404, slug="provisioning_bill-not-found")

        consumptions = ProvisioningUserConsumption.objects.filter(bills=bill).order_by("username")

        consumptions = handler.queryset(consumptions)
        serializer = GetProvisioningUserConsumptionDetailSerializer(consumptions, many=True)

        return handler.response(serializer.data)


class ProvisioningVendorView(APIView):
    """GET: list all provisioning vendors (id, name, workspaces_url). Academy from Academy header."""

    @capable_of("read_provisioning_activity")
    def get(self, request, academy_id=None):
        lang = get_user_language(request)
        vendor_type = _optional_vendor_type_from_query(request, lang=lang)
        vendors = ProvisioningVendor.objects.all().order_by("name")
        if vendor_type is not None:
            vendors = vendors.filter(vendor_type=vendor_type)
        serializer = GetProvisioningVendorSerializer(vendors, many=True)
        return Response(serializer.data)


class ProvisioningProfileView(APIView):
    """GET: list profiles for academy. POST: create profile (academy from Academy header)."""

    extensions = APIViewExtensions(paginate=True)

    @capable_of("read_provisioning_activity")
    def get(self, request, academy_id=None):
        handler = self.extensions(request)

        items = ProvisioningProfile.objects.filter(academy__id=academy_id).select_related("vendor", "academy")

        items = handler.queryset(items)
        serializer = GetProvisioningProfile(items, many=True)

        return handler.response(serializer.data)

    @capable_of("crud_provisioning_activity")
    def post(self, request, academy_id=None):
        lang = get_user_language(request)
        serializer = ProvisioningProfileCreateUpdateSerializer(data=request.data or {})
        if not serializer.is_valid():
            raise ValidationException(serializer.errors, code=400)
        data = serializer.validated_data
        vendor = ProvisioningVendor.objects.filter(id=data["vendor_id"]).first()
        if not vendor:
            raise ValidationException(
                translation(
                    lang,
                    en="Vendor not found.",
                    es="Vendor no encontrado.",
                    slug="vendor-not-found",
                ),
                code=404,
            )
        profile = ProvisioningProfile.objects.create(
            academy_id=academy_id,
            vendor=vendor,
        )
        if data.get("cohort_ids"):
            profile.cohorts.set(Cohort.objects.filter(id__in=data["cohort_ids"], academy_id=academy_id))
        if data.get("member_ids"):
            profile.members.set(ProfileAcademy.objects.filter(id__in=data["member_ids"], academy_id=academy_id))
        out = GetProvisioningProfile(profile)
        return Response(out.data, status=status.HTTP_201_CREATED)


class ProvisioningProfileByIdView(APIView):
    """GET one, PUT update, DELETE provisioning profile (academy from Academy header)."""

    @capable_of("read_provisioning_activity")
    def get(self, request, academy_id=None, profile_id=None):
        profile = (
            ProvisioningProfile.objects.filter(id=profile_id, academy__id=academy_id)
            .select_related("vendor", "academy")
            .first()
        )
        if not profile:
            raise ValidationException(
                translation(
                    get_user_language(request),
                    en="Provisioning profile not found.",
                    es="Perfil de aprovisionamiento no encontrado.",
                    slug="provisioning-profile-not-found",
                ),
                code=404,
            )
        serializer = GetProvisioningProfile(profile)
        return Response(serializer.data)

    @capable_of("crud_provisioning_activity")
    def put(self, request, academy_id=None, profile_id=None):
        lang = get_user_language(request)
        profile = ProvisioningProfile.objects.filter(id=profile_id, academy__id=academy_id).first()
        if not profile:
            raise ValidationException(
                translation(
                    lang,
                    en="Provisioning profile not found.",
                    es="Perfil de aprovisionamiento no encontrado.",
                    slug="provisioning-profile-not-found",
                ),
                code=404,
            )
        serializer = ProvisioningProfileCreateUpdateSerializer(data=request.data or {}, partial=True)
        if not serializer.is_valid():
            raise ValidationException(serializer.errors, code=400)
        data = serializer.validated_data
        if "vendor_id" in data:
            vendor = ProvisioningVendor.objects.filter(id=data["vendor_id"]).first()
            if not vendor:
                raise ValidationException(
                    translation(
                        lang,
                        en="Vendor not found.",
                        es="Vendor no encontrado.",
                        slug="vendor-not-found",
                    ),
                    code=404,
                )
            profile.vendor = vendor
            profile.save()
        if "cohort_ids" in data:
            profile.cohorts.set(Cohort.objects.filter(id__in=data["cohort_ids"], academy_id=academy_id))
        if "member_ids" in data:
            profile.members.set(ProfileAcademy.objects.filter(id__in=data["member_ids"], academy_id=academy_id))
        out = GetProvisioningProfile(profile)
        return Response(out.data)

    @capable_of("crud_provisioning_activity")
    def delete(self, request, academy_id=None, profile_id=None):
        lang = get_user_language(request)
        profile = ProvisioningProfile.objects.filter(id=profile_id, academy__id=academy_id).first()
        if not profile:
            raise ValidationException(
                translation(
                    lang,
                    en="Provisioning profile not found.",
                    es="Perfil de aprovisionamiento no encontrado.",
                    slug="provisioning-profile-not-found",
                ),
                code=404,
            )
        profile.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProvisioningAcademyView(APIView):
    """GET: list academy configs (credentials masked). POST: create academy config (academy from header)."""

    extensions = APIViewExtensions(paginate=True)

    @capable_of("read_provisioning_activity")
    def get(self, request, academy_id=None):
        lang = get_user_language(request)
        handler = self.extensions(request)
        vendor_type = _optional_vendor_type_from_query(request, lang=lang)
        items = (
            ProvisioningAcademy.objects.filter(academy_id=academy_id)
            .select_related("vendor", "academy")
            .prefetch_related("allowed_machine_types")
        )
        if vendor_type is not None:
            items = items.filter(vendor__vendor_type=vendor_type)
        items = handler.queryset(items)
        serializer = GetProvisioningAcademySerializer(items, many=True)
        return handler.response(serializer.data)

    @capable_of("crud_provisioning_activity")
    def post(self, request, academy_id=None):
        lang = get_user_language(request)
        serializer = ProvisioningAcademyCreateSerializer(data=request.data or {})
        if not serializer.is_valid():
            raise ValidationException(serializer.errors, code=400)
        data = serializer.validated_data
        vendor = ProvisioningVendor.objects.filter(id=data["vendor_id"]).first()
        if not vendor:
            raise ValidationException(
                translation(
                    lang,
                    en="Vendor not found.",
                    es="Vendor no encontrado.",
                    slug="vendor-not-found",
                ),
                code=404,
            )
        existing = ProvisioningAcademy.objects.filter(
            academy_id=academy_id,
            vendor=vendor,
        ).first()
        if existing:
            raise ValidationException(
                translation(
                    lang,
                    en="Provisioning config for this academy and vendor already exists.",
                    es="Ya existe una configuración de aprovisionamiento para esta academia y vendor.",
                    slug="provisioning-academy-already-exists",
                ),
                code=400,
            )

        pa = ProvisioningAcademy.objects.create(
            academy_id=academy_id,
            vendor=vendor,
            credentials_token=data["credentials_token"],
            credentials_key=data.get("credentials_key") or "",
            vendor_settings=validate_vendor_settings(vendor.name, data.get("vendor_settings") or {}, lang=lang),
            container_idle_timeout=data.get("container_idle_timeout", 15),
            max_active_containers=data.get("max_active_containers", 2),
        )
        if data.get("allowed_machine_type_ids"):
            machine_types = resolve_allowed_machine_types_for_vendor(
                vendor, data["allowed_machine_type_ids"], lang=lang
            )
            pa.allowed_machine_types.set(machine_types)
        out = GetProvisioningAcademySerializer(pa)
        return Response(out.data, status=status.HTTP_201_CREATED)


class ProvisioningAcademyByIdView(APIView):
    """GET one, PUT update, DELETE provisioning academy config (credentials never returned)."""

    @capable_of("read_provisioning_activity")
    def get(self, request, academy_id=None, provisioning_academy_id=None):
        pa = (
            ProvisioningAcademy.objects.filter(
                id=provisioning_academy_id,
                academy_id=academy_id,
            )
            .select_related("vendor", "academy")
            .first()
        )
        if not pa:
            raise ValidationException(
                translation(
                    get_user_language(request),
                    en="Provisioning academy config not found.",
                    es="Configuración de aprovisionamiento de academia no encontrada.",
                    slug="provisioning-academy-not-found",
                ),
                code=404,
            )
        serializer = GetProvisioningAcademySerializer(pa)
        return Response(serializer.data)

    @capable_of("crud_provisioning_activity")
    def put(self, request, academy_id=None, provisioning_academy_id=None):
        lang = get_user_language(request)
        pa = ProvisioningAcademy.objects.filter(
            id=provisioning_academy_id,
            academy_id=academy_id,
        ).first()
        if not pa:
            raise ValidationException(
                translation(
                    lang,
                    en="Provisioning academy config not found.",
                    es="Configuración de aprovisionamiento de academia no encontrada.",
                    slug="provisioning-academy-not-found",
                ),
                code=404,
            )
        serializer = ProvisioningAcademyUpdateSerializer(data=request.data or {}, partial=True)
        if not serializer.is_valid():
            raise ValidationException(serializer.errors, code=400)
        data = serializer.validated_data
        if "credentials_token" in data:
            pa.credentials_token = data["credentials_token"]
        if "credentials_key" in data:
            pa.credentials_key = data["credentials_key"]
        if "vendor_settings" in data:
            pa.vendor_settings = validate_vendor_settings(pa.vendor.name, data["vendor_settings"] or {}, lang=lang)
        if "container_idle_timeout" in data:
            pa.container_idle_timeout = data["container_idle_timeout"]
        if "max_active_containers" in data:
            pa.max_active_containers = data["max_active_containers"]
        if "allowed_machine_type_ids" in data:
            machine_types = resolve_allowed_machine_types_for_vendor(
                pa.vendor, data["allowed_machine_type_ids"], lang=lang
            )
            pa.allowed_machine_types.set(machine_types)
        pa.save()
        out = GetProvisioningAcademySerializer(pa)
        return Response(out.data)

    @capable_of("crud_provisioning_activity")
    def delete(self, request, academy_id=None, provisioning_academy_id=None):
        pa = ProvisioningAcademy.objects.filter(
            id=provisioning_academy_id,
            academy_id=academy_id,
        ).first()
        if not pa:
            raise ValidationException(
                translation(
                    get_user_language(request),
                    en="Provisioning academy config not found.",
                    es="Configuración de aprovisionamiento de academia no encontrada.",
                    slug="provisioning-academy-not-found",
                ),
                code=404,
            )
        pa.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProvisioningAcademyVendorOptionsView(APIView):
    """GET vendor options for one provisioning academy (unfiltered universe)."""

    @capable_of("crud_provisioning_activity")
    def get(self, request, academy_id=None, provisioning_academy_id=None):
        lang = get_user_language(request)
        pa = (
            ProvisioningAcademy.objects.filter(id=provisioning_academy_id, academy_id=academy_id)
            .select_related("vendor")
            .first()
        )
        if not pa:
            raise ValidationException(
                translation(
                    lang,
                    en="Provisioning academy config not found.",
                    es="Configuración de aprovisionamiento de academia no encontrada.",
                    slug="provisioning-academy-not-found",
                ),
                code=404,
            )

        vendor_slug = (getattr(pa.vendor, "name", "") or "").lower().strip()
        if vendor_slug not in ("hostinger", "digitalocean"):
            return Response(
                {
                    "catalog_items": [],
                    "templates": [],
                    "data_centers": [],
                    "regions": [],
                    "sizes": [],
                    "images": [],
                }
            )
        if not pa.credentials_token:
            raise ValidationException(
                translation(
                    lang,
                    en="Missing vendor token for this provisioning academy.",
                    es="Falta el token del vendor para esta configuración de aprovisionamiento.",
                    slug="missing-vendor-token",
                ),
                code=400,
            )

        if vendor_slug == "hostinger":
            options = _get_hostinger_vendor_options(pa.credentials_token, lang)
            return Response(options)
        options = _get_digitalocean_vendor_options(pa.credentials_token, lang)
        return Response(options)


class ProvisioningAcademyTestConnectionView(APIView):
    """POST test vendor API connection and persist status fields."""

    @capable_of("crud_provisioning_activity")
    def post(self, request, academy_id=None, provisioning_academy_id=None):
        lang = get_user_language(request)
        pa = (
            ProvisioningAcademy.objects.filter(id=provisioning_academy_id, academy_id=academy_id)
            .select_related("vendor")
            .first()
        )
        if not pa:
            raise ValidationException(
                translation(
                    lang,
                    en="Provisioning academy config not found.",
                    es="Configuración de aprovisionamiento de academia no encontrada.",
                    slug="provisioning-academy-not-found",
                ),
                code=404,
            )

        vendor = pa.vendor
        vendor_name = getattr(vendor, "name", "") if vendor else ""
        credentials = {"token": pa.credentials_token or ""}
        if pa.credentials_key:
            credentials["key"] = pa.credentials_key
        if pa.vendor_settings:
            credentials.update(pa.vendor_settings)

        try:
            if not vendor:
                raise ValidationException(
                    translation(
                        lang,
                        en="Provisioning vendor not found for this academy config.",
                        es="No se encontró el vendor de aprovisionamiento para esta configuración de academia.",
                        slug="provisioning-vendor-not-found",
                    ),
                    code=400,
                )

            vendor_type = getattr(vendor, "vendor_type", None)
            if vendor_type == ProvisioningVendor.VendorType.VPS_SERVER:
                client = get_vps_client(vendor)
                if not client:
                    raise VPSProvisioningError(f"No VPS client registered for vendor '{vendor_name}'")
                client.test_connection(credentials)
            elif vendor_type == ProvisioningVendor.VendorType.CODING_EDITOR:
                client = get_coding_editor_client(vendor)
                if not client:
                    raise CodingEditorConnectionError(f"No coding editor client registered for vendor '{vendor_name}'")
                client.test_connection(credentials, vendor=vendor)
            elif vendor_type == ProvisioningVendor.VendorType.LLM:
                client = get_llm_client(pa)
                if not client:
                    raise LLMConnectionError(f"No LLM client registered for vendor '{vendor_name}'")
                client.test_connection()
            else:
                raise ValidationException(
                    translation(
                        lang,
                        en=f"Unsupported vendor type '{vendor_type}'.",
                        es=f"Tipo de vendor no soportado '{vendor_type}'.",
                        slug="unsupported-vendor-type",
                    ),
                    code=400,
                )

            pa.connection_status = ProvisioningAcademy.ConnectionStatus.OK
            pa.connection_status_text = translation(
                lang,
                en="Vendor connection check succeeded.",
                es="La verificación de conexión del vendor fue exitosa.",
                slug="vendor-connection-check-succeeded",
            )
        except (
            VPSProvisioningError,
            CodingEditorConnectionError,
            LLMConnectionError,
            ValidationException,
            Exception,
        ) as e:
            pa.connection_status = ProvisioningAcademy.ConnectionStatus.ERROR
            if isinstance(e, ValidationException):
                pa.connection_status_text = str(e.detail)
            else:
                pa.connection_status_text = str(e)

        pa.connection_test_at = timezone.now()
        pa.save()
        serializer = GetProvisioningAcademySerializer(pa)
        return Response(serializer.data)


class MeVPSView(APIView):
    """GET: list current user's VPS. POST: request a new VPS (consumes vps_server consumable)."""

    extensions = APIViewExtensions(paginate=True)

    def get(self, request):
        handler = self.extensions(request)
        items = ProvisioningVPS.objects.filter(user=request.user).order_by("-created_at")
        items = handler.queryset(items)
        serializer = VPSListSerializer(items, many=True)
        return handler.response(serializer.data)

    def post(self, request):
        lang = get_user_language(request)
        data = (request.data or {}).copy()
        serializer = VPSRequestSerializer(data=data, context={"request": request, "lang": lang})
        if not serializer.is_valid():
            raise ValidationException(serializer.errors, code=400)
        plan_slug = (serializer.validated_data.get("plan_slug") or "").strip() or None
        _, provisioning_academy = get_eligible_academy_and_vendor_for_vps(request.user)
        vendor_selection = _build_vendor_selection(
            provisioning_academy.vendor.name,
            provisioning_academy.vendor_settings or {},
            serializer.validated_data,
            lang,
        )
        try:
            vps = request_vps(request.user, plan_slug=plan_slug, vendor_selection=vendor_selection)
        except ValidationException:
            raise
        out_serializer = VPSListSerializer(vps)
        return Response(out_serializer.data, status=status.HTTP_202_ACCEPTED)


class MeVPSByIdView(APIView):
    """GET: one VPS by id; only for owner; includes decrypted root_password for owner."""

    def get(self, request, vps_id):
        lang = get_user_language(request)
        vps = ProvisioningVPS.objects.filter(id=vps_id, user=request.user).first()
        if not vps:
            raise ValidationException(
                translation(
                    lang,
                    en="VPS not found or you do not have permission to view it.",
                    es="VPS no encontrado o no tienes permiso para verlo.",
                    slug="vps-not-found",
                ),
                code=404,
            )
        serializer = VPSDetailSerializer(vps, context={"show_password": True})
        return Response(serializer.data)


class AcademyVPSView(APIView):
    """GET: report of all VPS for the academy; optional ?user_id= to filter by student."""

    extensions = APIViewExtensions(paginate=True)

    @capable_of("crud_provisioning_activity")
    def get(self, request, academy_id=None):
        handler = self.extensions(request)
        qs = ProvisioningVPS.objects.filter(academy_id=academy_id).select_related("user").order_by("-created_at")
        user_id = request.GET.get("user_id")
        if user_id:
            try:
                uid = int(user_id)
                qs = qs.filter(user_id=uid)
            except ValueError:
                pass
        items = handler.queryset(qs)
        serializer = AcademyVPSListSerializer(items, many=True)
        return handler.response(serializer.data)

    @capable_of("crud_provisioning_activity")
    def post(self, request, academy_id=None):
        """Request a new VPS for a student; consumes the student's vps_server consumable."""
        lang = get_user_language(request)
        data = (request.data or {}).copy()
        serializer = AcademyVPSCreateSerializer(data=data, context={"request": request, "lang": lang})
        if not serializer.is_valid():
            raise ValidationException(serializer.errors, code=400)
        user_id = serializer.validated_data["user_id"]
        plan_slug = (serializer.validated_data.get("plan_slug") or "").strip() or None
        student = get_user_model().objects.filter(id=user_id).first()
        if not student:
            raise ValidationException(
                translation(
                    lang,
                    en="User not found.",
                    es="Usuario no encontrado.",
                    slug="user-not-found",
                ),
                code=404,
            )
        academy = Academy.objects.filter(id=academy_id).first()
        if not academy:
            raise ValidationException(
                translation(lang, en="Academy not found.", es="Academia no encontrada.", slug="academy-not-found"),
                code=404,
            )
        try:
            _, provisioning_academy = get_vps_provisioning_academy_for_academy(academy, lang=lang)
            vendor_selection = _build_vendor_selection(
                provisioning_academy.vendor.name,
                provisioning_academy.vendor_settings or {},
                serializer.validated_data,
                lang,
            )
            vps = request_vps_for_student(
                student, academy, plan_slug=plan_slug, vendor_selection=vendor_selection, lang=lang
            )
        except ValidationException:
            raise
        out_serializer = VPSListSerializer(vps)
        return Response(out_serializer.data, status=status.HTTP_202_ACCEPTED)


class AcademyVPSByIdView(APIView):
    """DELETE: academy deprovisions a student's VPS."""

    @capable_of("crud_provisioning_activity")
    def delete(self, request, academy_id=None, vps_id=None):
        lang = get_user_language(request)
        vps = (
            ProvisioningVPS.objects.filter(id=vps_id, academy_id=academy_id).select_related("vendor", "academy").first()
        )
        if not vps:
            raise ValidationException(
                translation(
                    lang,
                    en="VPS not found or it does not belong to this academy.",
                    es="VPS no encontrado o no pertenece a esta academia.",
                    slug="vps-not-found",
                ),
                code=404,
            )
        from breathecode.provisioning.tasks import deprovision_vps_task

        deprovision_vps_task.delay(vps.id)
        return Response(status=status.HTTP_204_NO_CONTENT)


# class ContainerMeView(APIView):
#     """
#     List all snippets, or create a new snippet.
#     """

#     @capable_of('get_containers')
#     def get(self, request, format=None, container_id=None):

#         containers = ProvisioningContainer.objects.filter(user=request.user)
#         lookup = {}

#         assignment = request.GET.get('assignment', None)
#         if assignment is not None:
#             lookup['task_associated_slug'] = assignment

#         like = request.GET.get('like', None)
#         if like is not None:
#             items = items.filter(display_name__icontains=like)

#         sort_by = '-created_at'
#         if 'sort' in self.request.GET and self.request.GET['sort'] != '':
#             sort_by = self.request.GET.get('sort')

#         items = items.filter(**lookup).order_by(sort_by)

#         page = self.paginate_queryset(items, request)
#         serializer = ContainerMeSmallSerializer(page, many=True)

#         if self.is_paginate(request):
#             return self.get_paginated_response(serializer.data)
#         else:
#             return Response(serializer.data, status=200)

#     @capable_of('create_container')
#     def post(self, request):

#         lang = get_user_language(request)

#         p_profile = ProvisioningProfile.objects.filter(profileacademy__user=request.user, profileacademy__academy__id=academy_id).first()
#         if p_profile is None:
#             raise ValidationException(translation(
#                 en="You don't have a provisioning profile for this academy, we don't know were or how to create the computer you will be using, please contact the academy",
#                 es="No hemos podido encontar un proveedor para aprovisionarte una computadora, por favor contacta tu academia"),
#                 slug='no-provisioning-profile')

#         serializer = ProvisioningContainerSerializer(
#                                         data=request.data,
#                                         context={
#                                             'request': request,
#                                             'academy_id': academy_id
#                                         })
#         if serializer.is_valid():
#             serializer.save()
#             return Response(serializer.data, status=status.HTTP_200_OK)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# @capable_of('crud_review')
# def delete(self, request, academy_id=None):
#     # TODO: here i don't add one single delete, because i don't know if it is required
#     lookups = self.generate_lookups(request, many_fields=['id'])
#     # automation_objects

#     if not lookups:
#         raise ValidationException('Missing parameters in the querystring', code=400)

#     items = Review.objects.filter(**lookups, academy__id=academy_id)

#     for item in items:
#         item.status = 'IGNORE'
#         item.save()

#     return Response(None, status=status.HTTP_204_NO_CONTENT)


class MeLLMKeysView(APIView):
    """GET: list keys from all academies. POST: create a new API key."""

    def get(self, request):
        lang = get_user_language(request)
        user = request.user
        if not Consumable.list(user=user, service="free-monthly-llm-budget").exists():
            raise ValidationException(
                translation(
                    lang,
                    en="You don't have the LLM budget consumable required to manage API keys.",
                    es="No tienes el consumible de presupuesto de LLM necesario para administrar llaves de API.",
                    slug="llm-budget-required",
                ),
                code=403,
            )

        academy_ids = (
            ProvisioningLLM.objects.filter(user=user)
            .exclude(status=ProvisioningLLM.STATUS_DEPROVISIONED)
            .values_list("academy_id", flat=True)
            .distinct()
        )
        all_keys = []
        token_ids: set[str] = set()
        for academy_id in academy_ids:
            provisioning_academy = resolve_provisioning_academy_for_llm(academy_id)
            if not provisioning_academy:
                continue

            client = get_llm_client(provisioning_academy)
            if client is None:
                continue

            provisioning_llm = ProvisioningLLM.objects.filter(
                user=user,
                academy_id=academy_id,
                vendor=provisioning_academy.vendor,
            ).first()

            academy_slug = getattr(provisioning_academy.academy, "slug", "") or str(academy_id)
            external_user_id = f"{user.username}-{academy_slug}"
            if provisioning_llm and provisioning_llm.external_user_id:
                external_user_id = provisioning_llm.external_user_id
            try:
                user_info = client.get_user_info(user_id=external_user_id)
            except LLMClientError:
                continue
            keys_data = user_info.get("keys") or []
            if not isinstance(keys_data, list):
                continue
            for item in keys_data:
                if not isinstance(item, dict):
                    continue

                token_id = item.get("token_id") or item.get("token")
                if not token_id:
                    continue
                # Avoid duplicated keys if multiple academies point to the same Litellm tenant.
                if token_id in token_ids:
                    continue
                token_ids.add(token_id)
                all_keys.append(
                    {
                        "token_id": token_id,
                        "key_alias": item.get("key_alias"),
                        "spend": item.get("spend"),
                        "created_at": item.get("created_at"),
                        "academy_id": academy_id,
                        "metadata": item.get("metadata") or {},
                    }
                )

        return Response(all_keys, status=status.HTTP_200_OK)

    def post(self, request):
        lang = get_user_language(request)
        alias = (request.data or {}).get("key_alias")
        plan_slug = (request.data or {}).get("plan_slug")
        if isinstance(alias, str):
            alias = alias.strip() or None
        else:
            alias = request.user.first_name or request.user.username
        if isinstance(plan_slug, str):
            plan_slug = plan_slug.strip() or None
        else:
            plan_slug = None

        plan_title = None
        if plan_slug:
            from breathecode.payments.models import Plan

            plan = Plan.objects.filter(slug=plan_slug).only("title").first()
            if not plan:
                raise ValidationException(
                    translation(
                        lang,
                        en="Plan not found.",
                        es="Plan no encontrado.",
                        slug="plan-not-found",
                    ),
                    code=404,
                )
            plan_title = plan.title
        try:
            client, external_user_id = resolve_llm_client_and_external_id(request, ensure_llm_user_record=True)
            metadata = {"plan_title": plan_title} if plan_title else None
            created = client.create_api_key(external_user_id=external_user_id, name=alias, metadata=metadata)
        except LLMClientError as exc:
            raise ValidationException(
                translation(
                    lang,
                    en=f"Error creating LLM API key: {exc}",
                    es=f"Error al crear la llave de API de LLM: {exc}",
                    slug="llm-key-create-error",
                ),
                code=502,
            )
        return Response(created, status=status.HTTP_201_CREATED)


class MeLLMKeyByIdView(APIView):
    """DELETE: delete a single key by token_id."""

    def delete(self, request, key_id):
        lang = get_user_language(request)
        try:
            client, external_user_id = resolve_llm_client_and_external_id(request)
            client.delete_api_keys(user_id=external_user_id, token_ids=[key_id])
        except LLMClientError as exc:
            raise ValidationException(
                translation(
                    lang,
                    en=f"Error deleting LLM API key: {exc}",
                    es=f"Error al borrar la llave de API de LLM: {exc}",
                    slug="llm-key-delete-error",
                ),
                code=502,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)
