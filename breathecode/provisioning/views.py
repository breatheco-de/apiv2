import hashlib
import math
import os
from datetime import date, datetime
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import pandas as pd
from circuitbreaker import CircuitBreakerError
from dateutil.relativedelta import relativedelta
from django.http import HttpResponse
from django.shortcuts import redirect, render
from rest_framework import status
from rest_framework.parsers import FileUploadParser, MultiPartParser
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_csv.renderers import CSVRenderer

from breathecode.admissions.models import Cohort, CohortUser
from breathecode.authenticate.actions import get_user_language
from breathecode.authenticate.models import ProfileAcademy
from breathecode.notify.actions import get_template_content
from breathecode.provisioning import tasks
from breathecode.provisioning.serializers import (
    GetProvisioningBillSerializer,
    GetProvisioningBillSmallSerializer,
    GetProvisioningUserConsumptionSerializer,
    ProvisioningBillHTMLSerializer,
    ProvisioningBillSerializer,
    ProvisioningUserConsumptionHTMLResumeSerializer,
)
from breathecode.utils import capable_of, cut_csv
from breathecode.utils.api_view_extensions.api_view_extensions import APIViewExtensions
from breathecode.utils.decorators import has_permission
from breathecode.utils.i18n import translation
from breathecode.utils.io.file import count_csv_rows
from breathecode.utils.views import private_view, render_message
from capyc.rest_framework.exceptions import ValidationException

from .actions import get_provisioning_vendor
from .models import BILL_STATUS, ProvisioningBill, ProvisioningUserConsumption


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
        return redirect(f"https://codespaces.new/?repo={url}")

    return render_message(
        request,
        f"Unknown provisioning vendor: '{vendor.name}', please speak with your program manager.",
        academy=cu.cohort.academy,
    )


def redirect_new_container_public(request):

    # user = token.user

    repo = request.GET.get("repo", None)
    if repo is None:
        return render_message(request, "Please specify a repository in the URL")

    urls = {"gitpod": "https://gitpod.io/#", "codespaces": "https://codespaces.new/?repo="}
    vendors = request.GET.get("vendor", "codespaces,gitpod").split(",")
    buttons = []
    for v in vendors:
        if v not in urls:
            return render_message(request, f"Invalid provisioning vendor: {v}")

        buttons.append({"label": f"Open in {v.capitalize()}", "url": (urls[v] + repo), "icon": f"/static/img/{v}.svg"})

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
                "Username",
                "Date",
                "Product",
                "SKU",
                "Quantity",
                "Unit Type",
                "Price Per Unit ($)",
                "Multiplier",
                "Owner",
            ]

        if format_error and len(df.keys().intersection(fields)) == len(fields):
            format_error = False

            csv_last_line = cut_csv(file, last=1)
            df2 = pd.read_csv(csv_last_line, sep=",", usecols=fields)
            df2.reset_index()

            try:

                first = df["Date"][0].split("-")
                last = df2["Date"][0].split("-")

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

            serializer = GetProvisioningBillSerializer(bill, many=False)
            return Response(serializer.data)

        items = ProvisioningBill.objects.filter(academy__id=academy_id)

        status = request.GET.get("status", None)
        if status is not None:
            items = items.filter(status__in=status.upper().split(","))

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
