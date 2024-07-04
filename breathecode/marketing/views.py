import csv
import datetime
import hashlib
import json
import logging
import os
import re
from datetime import timedelta
from urllib import parse

import pandas as pd
import pytz
from circuitbreaker import CircuitBreakerError
from django.contrib.auth.models import AnonymousUser
from django.db.models import CharField, Count, F, Func, Q, Value
from django.http import HttpResponse, HttpResponseNotFound, HttpResponseRedirect
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, renderer_classes
from rest_framework.exceptions import APIException
from rest_framework.parsers import FileUploadParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_csv.renderers import CSVRenderer

import breathecode.marketing.tasks as tasks
from breathecode.admissions.models import Academy
from breathecode.authenticate.actions import get_user_language
from breathecode.marketing.caches import CourseCache
from breathecode.monitoring.models import CSVUpload
from breathecode.renderers import PlainTextRenderer
from breathecode.services.activecampaign import ActiveCampaign
from breathecode.utils import GenerateLookupsMixin, HeaderLimitOffsetPagination, capable_of, localize_query
from breathecode.utils.api_view_extensions.api_view_extensions import APIViewExtensions
from breathecode.utils.decorators import validate_captcha, validate_captcha_challenge
from breathecode.utils.find_by_full_name import query_like_by_full_name
from breathecode.utils.i18n import translation
from capyc.rest_framework.exceptions import ValidationException

from .actions import convert_data_frame, sync_automations, sync_tags, validate_email
from .models import (
    AcademyAlias,
    ActiveCampaignAcademy,
    Automation,
    Course,
    Downloadable,
    FormEntry,
    LeadGenerationApp,
    ShortLink,
    Tag,
    UTMField,
)
from .serializers import (
    AcademyAliasSmallSerializer,
    ActiveCampaignAcademyBigSerializer,
    ActiveCampaignAcademySerializer,
    AutomationSmallSerializer,
    DownloadableSerializer,
    FormEntryBigSerializer,
    FormEntryHookSerializer,
    FormEntrySerializer,
    FormEntrySmallSerializer,
    GetCourseSerializer,
    LeadgenAppSmallSerializer,
    PostFormEntrySerializer,
    PUTAutomationSerializer,
    PUTTagSerializer,
    ShortLinkSerializer,
    ShortlinkSmallSerializer,
    TagSmallSerializer,
    UTMSmallSerializer,
)
from .tasks import async_activecampaign_webhook, persist_single_lead, update_link_viewcount

logger = logging.getLogger(__name__)
MIME_ALLOW = "text/csv"
SYSTEM_EMAIL = os.getenv("SYSTEM_EMAIL")

# Create your views here.


@api_view(["GET"])
@permission_classes([AllowAny])
def get_downloadable(request, slug=None):

    if slug is not None:
        download = Downloadable.objects.filter(slug=slug).first()
        if download is None:
            raise ValidationException("Document not found", 404, slug="not-found")

        if request.GET.get("raw", None) == "true":
            return HttpResponseRedirect(redirect_to=download.destination_url)

        seri = DownloadableSerializer(download, many=False)
        return Response(seri.data)

    items = Downloadable.objects.all()
    academy = request.GET.get("academy", None)
    if academy is not None:
        items = items.filter(academy__slug__in=academy.split(","))

    active = request.GET.get("active", None)
    if active is not None:
        if active == "true":
            active = True
        else:
            active = False
        items = items.filter(active=active)

    items = items.order_by("created_at")
    serializer = DownloadableSerializer(items, many=True)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([AllowAny])
def get_alias(request):

    items = AcademyAlias.objects.all()
    academy = request.GET.get("academy", None)
    if academy is not None:
        items = items.filter(academy__id__in=academy.split(","))

    serializer = AcademyAliasSmallSerializer(items, many=True)
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([AllowAny])
@validate_captcha_challenge
def create_lead(request):
    data = request.data.copy()

    # remove spaces from phone
    if "phone" in data:
        data["phone"] = data["phone"].replace(" ", "")

    if "utm_url" in data and ("//localhost:" in data["utm_url"] or "gitpod.io" in data["utm_url"]):
        print("Ignoring lead because its coming from development team")
        return Response(data, status=status.HTTP_201_CREATED)

    serializer = PostFormEntrySerializer(data=data)
    if serializer.is_valid():
        serializer.save()

        persist_single_lead.delay(serializer.data)

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([AllowAny])
@validate_captcha
def create_lead_captcha(request):
    data = request.data.copy()

    # remove spaces from phone
    if "phone" in data:
        data["phone"] = data["phone"].replace(" ", "")

    if "utm_url" in data and ("//localhost:" in data["utm_url"] or "gitpod.io" in data["utm_url"]):
        print("Ignoring lead because its coming from development team")
        return Response(data, status=status.HTTP_201_CREATED)

    serializer = PostFormEntrySerializer(data=data)
    if serializer.is_valid():
        serializer.save()

        persist_single_lead.delay(serializer.data)

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([AllowAny])
def create_lead_from_app(request, app_slug=None):

    app_id = request.GET.get("app_id", None)
    if app_id is None:
        raise ValidationException("Invalid app slug and/or id", code=400, slug="without-app-slug-or-app-id")

    if app_slug is None:
        # try get the slug from the encoded app_id
        decoded_id = parse.unquote(app_id)
        if ":" not in decoded_id:
            raise ValidationException("Missing app slug", code=400, slug="without-app-slug-or-app-id")
        else:
            app_slug, app_id = decoded_id.split(":")

    app = LeadGenerationApp.objects.filter(slug=app_slug, app_id=app_id).first()
    if app is None:
        raise ValidationException("App not found with those credentials", code=401, slug="without-app-id")

    app.hits += 1
    app.last_call_at = timezone.now()
    app.last_request_data = json.dumps(request.data)

    ## apply defaults from the app
    payload = {
        "location": app.location,
        "language": app.language,
        "utm_url": app.utm_url,
        "utm_medium": app.utm_medium,
        "utm_campaign": app.utm_campaign,
        "utm_source": app.utm_source,
        "utm_plan": app.utm_plan,
        "academy": app.academy.id,
        "lead_generation_app": app.id,
    }
    payload.update(request.data)

    if "automations" not in request.data:
        payload["automations"] = ",".join([str(auto.slug) for auto in app.default_automations.all()])

    if "tags" not in request.data:
        payload["tags"] = ",".join([tag.slug for tag in app.default_tags.all()])

    # remove spaces from phone
    if "phone" in request.data:
        payload["phone"] = payload["phone"].replace(" ", "")

    serializer = PostFormEntrySerializer(data=payload)
    if serializer.is_valid():
        serializer.save()

        tasks.persist_single_lead.delay(serializer.data)

        app.last_call_status = "OK"
        app.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    else:
        app.last_call_status = "ERROR"
        app.last_call_log = json.dumps(serializer.errors)
        app.save()

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([AllowAny])
def validate_email_from_app(request):

    lang = get_user_language(request)
    data = request.data.copy()

    email = data["email"] if "email" in data else None
    if email is None:
        raise ValidationException("Please provide an email to validate", code=400, slug="without-email")

    try:
        payload = validate_email(email, lang)
        return Response(payload, status=status.HTTP_200_OK)
    except ValidationException as e:
        raise e
    except Exception:

        raise ValidationException(
            translation(
                lang,
                en="Error while validating email address",
                es="Se ha producido un error validando tu dirección de correo electrónico",
                slug="email-validation-error",
            )
        )


@api_view(["POST"])
@permission_classes([AllowAny])
@renderer_classes([PlainTextRenderer])
def activecampaign_webhook(request, ac_academy_id=None, academy_slug=None):

    if ac_academy_id is not None:
        a = Academy.objects.filter(slug=ac_academy_id).first()
        if a is None:
            raise APIException(f"Academy not found (id:{ac_academy_id}) ")
        webhook = ActiveCampaign.add_webhook_to_log(request.data, a.slug)
    elif academy_slug is not None:
        webhook = ActiveCampaign.add_webhook_to_log(request.data, academy_slug)
    else:
        raise APIException("Please specify a valid academy slug or id")

    if webhook:
        async_activecampaign_webhook.delay(webhook.id)
    else:
        logger.debug("One request cannot be parsed, maybe you should update `ActiveCampaign" ".add_webhook_to_log`")
        # logger.debug(request.data)

    # async_eventbrite_webhook(request.data)
    return Response("ok", content_type="text/plain")


@api_view(["GET"])
@permission_classes([AllowAny])
@renderer_classes([CSVRenderer])
def googleads_enrollments(request, academy_slugs):

    slugs = academy_slugs.split(",")
    academies = FormEntry.objects.filter(Q(academy__slug__in=slugs) | Q(ac_academy__academy__slug__in=slugs)).exclude(
        gclid__isnull=True
    )

    serializer = FormEntrySerializer(academies, many=True)
    return Response(serializer.data)


# Create your views here.


@api_view(["POST", "GET"])
@permission_classes([AllowAny])
def receive_facebook_lead(request):
    if request.method == "GET":

        challenge = "no challenge"
        if "hub.challenge" in request.GET:
            challenge = request.GET["hub.challenge"]

        verify_token = ""
        if "hub.verify_token" in request.GET:
            verify_token = request.GET["hub.verify_token"]

        if verify_token == os.getenv("FACEBOOK_VERIFY_TOKEN", ""):
            return Response(int(challenge), status=status.HTTP_200_OK)
        else:
            return Response(int(challenge), status=status.HTTP_400_BAD_REQUEST)
    else:
        if "object" in request.data:
            if request.data["object"] == "page":
                for entry in request.data["entry"]:
                    for changes in entry["changes"]:
                        if changes["field"] == "leadgen":
                            serializer = PostFormEntrySerializer(
                                data={
                                    "fb_leadgen_id": changes["value"]["leadgen_id"],
                                    "fb_page_id": changes["value"]["page_id"],
                                    "fb_form_id": changes["value"]["form_id"],
                                    "fb_adgroup_id": changes["value"]["adgroup_id"],
                                    "fb_ad_id": changes["value"]["ad_id"],
                                }
                            )
                            if serializer.is_valid():
                                serializer.save()
                                # persist_single_lead.delay(request.data)
                                return Response(serializer.data, status=status.HTTP_201_CREATED)
                            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    return Response({"details": "No leads found"}, status=status.HTTP_400_BAD_REQUEST)


# Create your views here.
@api_view(["GET"])
def sync_tags_with_active_campaign(request, academy_id):

    academy = ActiveCampaignAcademy.objects.filter(academy__id=academy_id).first()
    if academy is None:
        raise APIException("Academy not found")

    tags = sync_tags(academy)
    return Response(tags, status=status.HTTP_200_OK)


# Create your views here.


@api_view(["GET"])
def sync_automations_with_active_campaign(request, academy_id):

    academy = ActiveCampaignAcademy.objects.filter(academy__id=academy_id).first()
    if academy is None:
        raise APIException("Academy not found")

    tags = sync_automations(academy)
    return Response(tags, status=status.HTTP_200_OK)


def redirect_link(request, link_slug):
    short_link = ShortLink.objects.filter(slug=link_slug, active=True).first()
    if short_link is None:
        return HttpResponseNotFound("URL not found")

    update_link_viewcount.delay(short_link.slug)

    params = {}
    if short_link.utm_source is not None:
        params["utm_source"] = short_link.utm_source
    if short_link.utm_content is not None:
        params["utm_content"] = short_link.utm_content
    if short_link.utm_medium is not None:
        params["utm_medium"] = short_link.utm_medium
    if short_link.utm_campaign is not None:
        params["utm_campaign"] = short_link.utm_campaign

    destination_params = {}
    url_parts = short_link.destination.split("?")
    if len(url_parts) > 1:
        destination_params = dict(parse.parse_qsl(url_parts[1]))

    params = {**destination_params, **params}
    return HttpResponseRedirect(redirect_to=url_parts[0] + "?" + parse.urlencode(params))


@api_view(["GET"])
def get_leads(request, id=None):

    items = FormEntry.objects.all()
    if isinstance(request.user, AnonymousUser) == False:
        items = localize_query(items, request)

    academy = request.GET.get("academy", None)
    if academy is not None:
        items = items.filter(academy__slug__in=academy.split(","))

    start = request.GET.get("start", None)
    if start is not None:
        start_date = datetime.datetime.strptime(start, "%Y-%m-%d").date()
        items = items.filter(created_at__gte=start_date)

    end = request.GET.get("end", None)
    if end is not None:
        end_date = datetime.datetime.strptime(end, "%Y-%m-%d").date()
        items = items.filter(created_at__lte=end_date)

    items = items.order_by("created_at")
    serializer = FormEntrySerializer(items, many=True)
    return Response(serializer.data)


@api_view(["GET"])
def get_leads_report(request, id=None):

    items = FormEntry.objects.all()

    if isinstance(request.user, AnonymousUser) == False:
        # filter only to the local academy
        items = localize_query(items, request)

    group_by = request.GET.get("by", "location,created_at__date,course")
    if group_by != "":
        group_by = group_by.split(",")
    else:
        group_by = ["location", "created_at__date", "course"]

    academy = request.GET.get("academy", None)
    if academy is not None:
        items = items.filter(location__in=academy.split(","))

    start = request.GET.get("start", None)
    if start is not None:
        start_date = datetime.datetime.strptime(start, "%Y-%m-%d").date()
        items = items.filter(created_at__gte=start_date)

    end = request.GET.get("end", None)
    if end is not None:
        end_date = datetime.datetime.strptime(end, "%Y-%m-%d").date()
        items = items.filter(created_at__lte=end_date)

    items = items.values(*group_by).annotate(total_leads=Count("location"))

    if "created_at__date" in group_by:
        items = items.annotate(
            created_date=Func(F("created_at"), Value("YYYYMMDD"), function="to_char", output_field=CharField())
        )
    # items = items.order_by('created_at')
    return Response(items)


class AcademyTagView(APIView, GenerateLookupsMixin):
    """
    List all snippets, or create a new snippet.
    """

    extensions = APIViewExtensions(sort="-created_at", paginate=True)

    @capable_of("read_tag")
    def get(self, request, format=None, academy_id=None):
        handler = self.extensions(request)

        items = Tag.objects.filter(ac_academy__academy__id=academy_id)

        like = request.GET.get("like", None)
        if like is not None:
            items = items.filter(slug__icontains=like)

        status = request.GET.get("status", None)
        if status is not None:
            aproved = True
            if status == "DISPUTED":
                aproved = False
            items = items.filter(disputed_at__isnull=aproved)

        types = request.GET.get("type", None)
        if types is not None:
            _types = types.split(",")
            items = items.filter(tag_type__in=[x.upper() for x in _types])

        items = handler.queryset(items)
        serializer = TagSmallSerializer(items, many=True)
        return handler.response(serializer.data)

    @capable_of("crud_tag")
    def put(self, request, tag_slug=None, academy_id=None):
        many = isinstance(request.data, list)
        if not many:
            tag = Tag.objects.filter(slug=tag_slug, ac_academy__academy__id=academy_id).first()
            if tag is None:
                raise ValidationException(f"Tag {tag_slug} not found for this academy", slug="tag-not-found")
        else:
            tag = []
            index = -1
            for x in request.data:
                index = index + 1

                if "id" not in x:
                    raise ValidationException("Cannot determine tag in " f"index {index}", slug="without-id")

                instance = Tag.objects.filter(id=x["id"], ac_academy__academy__id=academy_id).first()

                if not instance:
                    raise ValidationException(
                        f'Tag({x["id"]}) does not exist on this academy', code=404, slug="not-found"
                    )
                tag.append(instance)
        serializer = PUTTagSerializer(
            tag, data=request.data, context={"request": request, "academy": academy_id}, many=many
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AcademyAutomationView(APIView, GenerateLookupsMixin):
    """
    List all snippets, or create a new snippet.
    """

    extensions = APIViewExtensions(sort="-created_at", paginate=True)

    @capable_of("read_tag")
    def get(self, request, format=None, academy_id=None):
        handler = self.extensions(request)
        items = Automation.objects.filter(ac_academy__academy__id=academy_id)

        like = request.GET.get("like", None)
        if like is not None:
            items = items.filter(Q(slug__icontains=like) | Q(name__icontains=like))

        status = request.GET.get("status", None)
        if status is not None:
            _status = status.split(",")
            items = items.filter(status__in=[x.upper() for x in _status])

        items = handler.queryset(items)
        serializer = AutomationSmallSerializer(items, many=True)
        return handler.response(serializer.data)

    @capable_of("crud_tag")
    def put(self, request, automation_id=None, academy_id=None):
        many = isinstance(request.data, list)
        if not many:
            automation = Automation.objects.filter(id=automation_id, ac_academy__academy__id=academy_id).first()
            if automation is None:
                raise ValidationException(
                    f"Automation {automation_id} not found for this academy", slug="automation-not-found"
                )
        else:
            automation = []
            index = -1
            for x in request.data:
                index = index + 1

                if "id" not in x:
                    raise ValidationException("Cannot determine automation in " f"index {index}", slug="without-id")

                instance = Automation.objects.filter(id=x["id"], ac_academy__academy__id=academy_id).first()

                if not instance:
                    raise ValidationException(
                        f'Automation({x["id"]}) does not exist on this academy', code=404, slug="not-found"
                    )
                automation.append(instance)
        serializer = PUTAutomationSerializer(
            automation, data=request.data, context={"request": request, "academy": academy_id}, many=many
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AcademyAppView(APIView, GenerateLookupsMixin):
    """
    List all snippets, or create a new snippet.
    """

    @capable_of("read_lead_gen_app")
    def get(self, request, academy_id=None):

        apps = LeadGenerationApp.objects.filter(academy__id=academy_id)

        serializer = LeadgenAppSmallSerializer(apps, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AcademyAliasView(APIView, GenerateLookupsMixin):
    """
    List all snippets, or create a new snippet.
    """

    @capable_of("read_my_academy")
    def get(self, request, academy_id):

        alias = AcademyAlias.objects.filter(academy__id=academy_id)

        serializer = AcademyAliasSmallSerializer(alias, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class UTMView(APIView, GenerateLookupsMixin):
    """
    List all snippets, or create a new snippet.
    """

    @capable_of("read_lead")
    def get(self, request, format=None, academy_id=None):

        utms = UTMField.objects.filter(academy__id=academy_id)

        like = request.GET.get("like", None)
        if like is not None:
            utms = utms.filter(slug__icontains=like)

        types = request.GET.get("type", None)
        if types is not None:
            _types = types.split(",")
            utms = utms.filter(utm_type__in=[x.upper() for x in _types])

        serializer = UTMSmallSerializer(utms, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AcademyWonLeadView(APIView, HeaderLimitOffsetPagination, GenerateLookupsMixin):
    """
    List all snippets, or create a new snippet.
    """

    @capable_of("read_won_lead")
    def get(self, request, format=None, academy_id=None):

        academy = Academy.objects.get(id=academy_id)
        items = FormEntry.objects.filter(academy__id=academy.id, deal_status="WON")
        lookup = {}

        start = request.GET.get("start", "")
        if start != "":
            start_date = datetime.datetime.strptime(start, "%Y-%m-%d").date()
            lookup["created_at__gte"] = start_date

        end = request.GET.get("end", "")
        if end != "":
            end_date = datetime.datetime.strptime(end, "%Y-%m-%d").date()
            lookup["created_at__lte"] = end_date

        if "storage_status" in self.request.GET:
            param = self.request.GET.get("storage_status")
            lookup["storage_status"] = param

        course = request.GET.get("course", "")
        if course != "":
            lookup["course__in"] = course.split(",")

        location = request.GET.get("location", "")
        if location != "":
            lookup["location__in"] = location.split(",")

        sort_by = "-created_at"
        if "sort" in self.request.GET and self.request.GET["sort"] != "":
            sort_by = self.request.GET.get("sort")

        items = items.filter(**lookup).order_by(sort_by)

        like = request.GET.get("like", None)
        if like is not None:
            items = query_like_by_full_name(like=like, items=items)

        page = self.paginate_queryset(items, request)
        serializer = FormEntrySmallSerializer(page, many=True)

        if self.is_paginate(request):
            return self.get_paginated_response(serializer.data)
        else:
            return Response(serializer.data, status=200)


class AcademyProcessView(APIView, GenerateLookupsMixin):

    @capable_of("crud_lead")
    def put(self, request, academy_id=None):
        lookups = self.generate_lookups(request, many_fields=["id"])
        if not lookups:
            raise ValidationException("Missing id parameters in the querystring", code=400)

        items = FormEntry.objects.filter(**lookups, academy__id=academy_id)
        for item in items:
            persist_single_lead.delay(item.to_form_data())

        return Response({"details": f"{items.count()} leads added to the processing queue"}, status=status.HTTP_200_OK)


class AcademyLeadView(APIView, GenerateLookupsMixin):
    """
    List all snippets, or create a new snippet.
    """

    extensions = APIViewExtensions(sort="-created_at", paginate=True)

    @capable_of("read_lead")
    def get(self, request, academy_id=None, lead_id=None):
        handler = self.extensions(request)

        if lead_id is not None:
            single_lead = FormEntry.objects.filter(id=lead_id, academy__id=academy_id).first()
            if single_lead is None:
                raise ValidationException(f"Lead {lead_id} not found", 404, slug="lead-not-found")

            serializer = FormEntryBigSerializer(single_lead, many=False)
            return handler.response(serializer.data)

        academy = Academy.objects.get(id=academy_id)
        items = FormEntry.objects.filter(academy__id=academy.id)
        lookup = {}

        start = request.GET.get("start", None)
        if start is not None:
            start_date = datetime.datetime.strptime(start, "%Y-%m-%d").date()
            lookup["created_at__gte"] = start_date

        end = request.GET.get("end", None)
        if end is not None:
            end_date = datetime.datetime.strptime(end, "%Y-%m-%d").date()
            lookup["created_at__lte"] = end_date

        if "storage_status" in self.request.GET:
            param = self.request.GET.get("storage_status")
            lookup["storage_status"] = param

        if "deal_status" in self.request.GET:
            param = self.request.GET.get("deal_status")
            lookup["deal_status"] = param.upper()

        if "course" in self.request.GET:
            param = self.request.GET.get("course")
            lookup["course__in"] = [x.strip() for x in param.split(",")]

        if "ac_deal_id" in self.request.GET:
            param = self.request.GET.get("ac_deal_id")
            lookup["ac_deal_id"] = param

        if "location" in self.request.GET or "location_alias" in self.request.GET:
            param = (
                self.request.GET.get("location")
                if self.request.GET.get("location") is not None
                else self.request.GET.get("location_alias")
            )
            lookup["location__in"] = [x.strip() for x in param.split(",")]

        if "deal_location" in self.request.GET:
            param = self.request.GET.get("deal_location")
            lookup["ac_deal_location__in"] = [x.strip() for x in param.split(",")]

        if "deal_course" in self.request.GET:
            param = self.request.GET.get("deal_course")
            lookup["ac_deal_course__in"] = [x.strip() for x in param.split(",")]

        if "utm_medium" in self.request.GET:
            param = self.request.GET.get("utm_medium")
            items = items.filter(utm_medium__icontains=param)

        if "utm_url" in self.request.GET:
            param = self.request.GET.get("utm_url")
            items = items.filter(utm_url__icontains=param)

        if "utm_campaign" in self.request.GET:
            param = self.request.GET.get("utm_campaign")
            items = items.filter(utm_campaign__icontains=param)

        if "utm_source" in self.request.GET:
            param = self.request.GET.get("utm_source")
            items = items.filter(utm_source__icontains=param)

        if "utm_term" in self.request.GET:
            param = self.request.GET.get("utm_term")
            items = items.filter(utm_term__icontains=param)

        if "tags" in self.request.GET:
            lookups = self.generate_lookups(request, many_fields=["tags"])
            items = items.filter(tag_objects__slug__in=lookups["tags__in"])

        items = items.filter(**lookup)

        like = request.GET.get("like", None)
        if like is not None:
            items = query_like_by_full_name(like=like, items=items)

        items = handler.queryset(items)

        only_first = request.GET.get("only_first", None)
        if only_first is not None and only_first.lower() == "true":
            first = items.first()
            first = [first] if first is not None else []
            serializer = FormEntryHookSerializer(first, many=True)

        else:
            serializer = FormEntrySmallSerializer(items, many=True)

        return handler.response(serializer.data)

    @capable_of("crud_lead")
    def post(self, request, academy_id=None):

        academy = Academy.objects.filter(id=academy_id).first()
        if academy is None:
            raise ValidationException(f"Academy {academy_id} not found", slug="academy-not-found")

        # ignore the incoming location information and override with the session academy
        data = {**request.data, "location": academy.active_campaign_slug}

        serializer = PostFormEntrySerializer(data=data, context={"request": request, "academy": academy_id})
        if serializer.is_valid():
            serializer.save()
            big_serializer = FormEntryBigSerializer(serializer.instance)
            return Response(big_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of("crud_lead")
    def put(self, request, academy_id=None, lead_id=None):
        academy = Academy.objects.filter(id=academy_id).first()
        if academy is None:
            raise ValidationException(f"Academy {academy_id} not found", slug="academy-not-found")

        lookups = None
        if lead_id is not None:
            lookups = {"id": lead_id}
        else:
            lookups = self.generate_lookups(request, many_fields=["id"])

        if not lookups and lead_id is None:
            raise ValidationException("Missing lead ids parameters in the querystring", code=400)

        leads = FormEntry.objects.filter(**lookups, academy__id=academy_id)
        if leads.count() == 0:
            raise ValidationException("Leads not found", slug="lead-not-found")

        data = {**request.data}

        serializers = []
        for lead in leads:
            serializer = PostFormEntrySerializer(lead, data=data, context={"request": request, "academy": academy_id})
            serializers.append(serializer)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        for s in serializers:
            s.save()

        if len(serializers) == 1:
            big_serializer = FormEntryBigSerializer(serializer.instance)
        else:
            big_serializer = FormEntryBigSerializer(leads, many=True)

        return Response(big_serializer.data, status=status.HTTP_200_OK)

    @capable_of("crud_lead")
    def delete(self, request, academy_id=None):
        # TODO: here i don't add one single delete, because i don't know if it is required
        lookups = self.generate_lookups(request, many_fields=["id"])
        # automation_objects

        if not lookups:
            raise ValidationException("Missing parameters in the querystring", code=400)

        items = FormEntry.objects.filter(**lookups, academy__id=academy_id)

        for item in items:
            item.delete()

        return Response(None, status=status.HTTP_204_NO_CONTENT)


class ActiveCampaignView(APIView, GenerateLookupsMixin):
    """
    List all snippets, or create a new snippet.
    """

    @capable_of("read_lead")
    def get(self, request, academy_id=None):

        ac_academy = ActiveCampaignAcademy.objects.filter(academy__id=academy_id).first()
        if ac_academy is None:
            raise ValidationException("Active Campaign Academy not found", 404)

        serializer = ActiveCampaignAcademyBigSerializer(ac_academy)
        return Response(serializer.data, status=200)

    @capable_of("crud_lead")
    def post(self, request, academy_id=None):

        serializer = ActiveCampaignAcademySerializer(
            data=request.data, context={"request": request, "academy": academy_id}
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of("crud_lead")
    def put(self, request, ac_id, academy_id=None):

        ac_academy = ActiveCampaignAcademy.objects.filter(id=ac_id, academy__id=academy_id).first()
        if ac_academy is None:
            raise ValidationException(f"Active Campaign {ac_id} not found", slug="active-campaign-not-found")
        serializer = ActiveCampaignAcademySerializer(
            ac_academy, data=request.data, context={"request": request, "academy": academy_id}
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ShortLinkView(APIView, HeaderLimitOffsetPagination, GenerateLookupsMixin):
    """
    List all snippets, or create a new snippet.
    """

    @capable_of("read_shortlink")
    def get(self, request, slug=None, academy_id=None):

        if slug is not None:
            link = ShortLink.objects.filter(slug=slug).first()
            if link is None or (link.private and link.academy.id != academy_id):
                raise ValidationException(
                    f"Shortlink with slug {slug} not found or its private and it belongs to another academy",
                    slug="shortlink-not-found",
                )

        academy = Academy.objects.get(id=academy_id)
        items = ShortLink.objects.filter(Q(academy__id=academy.id) | Q(private=False))
        lookup = {}

        private = request.GET.get("private", None)
        if private == "true":
            lookup["private"] = True

        sort_by = "-created_at"
        if "sort" in self.request.GET and self.request.GET["sort"] != "":
            sort_by = self.request.GET.get("sort")

        items = items.filter(**lookup).order_by(sort_by)

        like = request.GET.get("like", None)
        if like is not None:
            items = items.filter(slug__icontains=like)

        page = self.paginate_queryset(items, request)
        serializer = ShortlinkSmallSerializer(page, many=True)

        if self.is_paginate(request):
            return self.get_paginated_response(serializer.data)
        else:
            return Response(serializer.data, status=200)

    @capable_of("crud_shortlink")
    def post(self, request, academy_id=None):

        serializer = ShortLinkSerializer(data=request.data, context={"request": request, "academy": academy_id})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of("crud_shortlink")
    def put(self, request, short_slug, academy_id=None):

        short = ShortLink.objects.filter(slug=short_slug, academy__id=academy_id).first()
        if short is None:
            raise ValidationException(f"ShortLink {short_slug} not found", slug="short-not-found")

        serializer = ShortLinkSerializer(short, data=request.data, context={"request": request, "academy": academy_id})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of("crud_shortlink")
    def delete(self, request, academy_id=None):
        # TODO: here i don't add one single delete, because i don't know if it is required
        lookups = self.generate_lookups(request, many_fields=["id"])
        # automation_objects

        if not lookups:
            raise ValidationException("Missing parameters in the querystring", code=400)

        items = ShortLink.objects.filter(**lookups, academy__id=academy_id)
        for i in items:
            utc_now = timezone.now()
            days_ago = i.created_at + timedelta(days=1)
            if days_ago < utc_now:
                raise ValidationException(
                    "You cannot update or delete short links that have been created more than 1 day ago, create a new link instead",
                    slug="update-days-ago",
                )

        items.delete()

        return Response(None, status=status.HTTP_204_NO_CONTENT)


class UploadView(APIView):
    """
    put:
        Upload a file to Google Cloud.
    """

    parser_classes = [MultiPartParser, FileUploadParser]

    # permission_classes = [AllowAny]

    # upload was separated because in one moment I think that the serializer
    # not should get many create and update operations together
    def upload(self, file, lang, academy_id=None, update=False):
        from ..services.google_cloud import Storage

        if not file:
            raise ValidationException("Missing file in request", code=400)

        # files validation below
        if file.content_type != MIME_ALLOW:
            raise ValidationException(f"You can upload only files on the following formats: {MIME_ALLOW}")

        file_bytes = file.read()

        file_name = hashlib.sha256(file_bytes).hexdigest()

        file_bytes = file_bytes.decode("utf-8")

        with open(file.name, "w") as f:
            f.write(file_bytes)
        df = pd.read_csv(file.name)
        os.remove(file.name)
        required_fields = ["first_name", "last_name", "email", "location", "phone", "language"]

        # Think about uploading correct files and leaving out incorrect ones
        for item in required_fields:
            if item not in df.keys():
                return ValidationException(f"{item} field missing inside of csv")

        data = {"file_name": file.name, "status": "PENDING", "message": "Despues"}

        # upload file section
        try:
            storage = Storage()
            cloud_file = storage.file(os.getenv("DOWNLOADS_BUCKET", None), file_name)
            cloud_file.upload(file, content_type=file.content_type)

            csv_upload = CSVUpload()
            csv_upload.url = cloud_file.url()
            csv_upload.name = file.name
            csv_upload.hash = file_name
            csv_upload.academy_id = academy_id
            csv_upload.save()

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

        for num in range(len(df)):
            value = df.iloc[num]
            logger.info(dict(value))
            parsed = convert_data_frame(dict(value))
            tasks.create_form_entry.delay(csv_upload.id, **parsed)

        return data

    @capable_of("crud_media")
    def put(self, request, academy_id=None):
        lang = get_user_language(request)
        files = request.data.getlist("file")
        result = []
        for file in files:
            upload = self.upload(file, lang, academy_id, update=True)
            result.append(upload)
        return Response(result, status=status.HTTP_200_OK)


def get_real_conversion_name(slug):
    mapper = {
        "Website Lead": "Application Submitted",
    }
    words = re.split(" |_|-", slug)
    words = [w.capitalize() for w in words]
    words = " ".join(words)
    if words in mapper:
        words = mapper[words]

    return words


def googleads_csv(request):

    ids = request.GET.get("academy", "")
    slugs = request.GET.get("academy_slug", "")

    ids = ids.split(",") if ids else []
    slugs = slugs.split(",") if slugs else []

    if ids:
        form_entries = FormEntry.objects.filter(academy__id__in=ids).order_by("id")

    elif slugs:
        form_entries = FormEntry.objects.filter(academy__slug__in=slugs).order_by("id")

    else:
        form_entries = FormEntry.objects.all()

    if Academy.objects.filter(id__in=ids).count() != len(ids) or Academy.objects.filter(slug__in=slugs).count() != len(
        slugs
    ):
        raise ValidationException("Some academy not exist", slug="academy-not-found")

    data = []
    response = HttpResponse(
        content_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="googleads.csv"'},
    )

    for entry in form_entries:

        if entry.gclid:
            entry_gclid = entry.gclid[-4:]

            if entry_gclid == "_BwE" and entry.deal_status == "WON":
                gclid = entry.gclid
                convertion_name = get_real_conversion_name(entry.tags)

                timezone = pytz.timezone("US/Eastern")
                if entry.won_at is not None:
                    convertion_time = entry.won_at.astimezone(timezone)
                else:
                    convertion_time = entry.updated_at.astimezone(timezone)

                convertion_time = convertion_time.strftime("%Y-%m-%d %H:%M:%S")

                data.append([gclid, convertion_name, convertion_time, None, None])

    writer = csv.writer(response)
    writer.writerow(["Parameters:TimeZone=US/Eastern"])
    writer.writerow(
        ["Google Click ID", "Conversion Name", "Conversion Time", "Conversion Value", "Conversion Currency"]
    )

    for d in data:
        writer.writerow(d)

    return response


class CourseView(APIView):
    permission_classes = [AllowAny]
    extensions = APIViewExtensions(cache=CourseCache, sort="-updated_at", paginate=True)

    def get_lookup(self, key, value):
        args = ()
        kwargs = {}
        slug_key = f"{key}__slug__in"
        pk_key = f"{key}__id__in"

        for v in value.split(","):
            if slug_key not in kwargs and not v.isnumeric():
                kwargs[slug_key] = []

            if pk_key not in kwargs and v.isnumeric():
                kwargs[pk_key] = []

            if v.isnumeric():
                kwargs[pk_key].append(int(v))

            else:
                kwargs[slug_key].append(v)

        if len(kwargs) > 1:
            args = (Q(**{slug_key: kwargs[slug_key]}) | Q(**{pk_key: kwargs[pk_key]}),)
            kwargs = {}

        return args, kwargs

    def get(self, request, course_slug=None):
        handler = self.extensions(request)

        cache = handler.cache.get()
        if cache is not None:
            return cache

        lang = request.GET.get("lang")
        if lang is None:
            lang = get_user_language(request)

        if course_slug:
            item = (
                Course.objects.filter(slug=course_slug)
                .annotate(lang=Value(lang, output_field=CharField()))
                .exclude(status="DELETED")
                .exclude(visibility="PRIVATE")
                .first()
            )

            if not item:
                raise ValidationException(
                    translation(lang, en="Course not found", es="Curso no encontrado", slug="course-not-found"),
                    code=404,
                )

            serializer = GetCourseSerializer(item, context={"lang": lang}, many=False)
            return handler.response(serializer.data)

        items = Course.objects.filter().exclude(status="DELETED").exclude(visibility="PRIVATE")

        if academy := request.GET.get("academy"):
            args, kwargs = self.get_lookup("academy", academy)
            items = items.filter(*args, **kwargs)

        if syllabus := request.GET.get("syllabus"):
            args, kwargs = self.get_lookup("syllabus", syllabus)
            items = items.filter(*args, **kwargs)

        if s := request.GET.get("status"):
            items = items.filter(status__in=s.split(","))

        else:
            items = items.exclude(status="ARCHIVED")

        if icon_url := request.GET.get("icon_url"):
            items = items.filter(icon_url__icontains=icon_url)

        if technologies := request.GET.get("technologies"):
            technologies = technologies.split(",")
            query = Q(technologies__icontains=technologies[0])
            for technology in technologies[1:]:
                query |= Q(technologies__icontains=technology)

            items = items.filter(query)

        items = items.annotate(lang=Value(lang, output_field=CharField()))
        items = items.order_by("created_at")
        items = handler.queryset(items)
        serializer = GetCourseSerializer(items, context={"lang": lang}, many=True)
        return handler.response(serializer.data)
