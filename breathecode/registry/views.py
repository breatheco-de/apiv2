import logging
import os
import re
from pathlib import Path

import requests
from capyc.core.i18n import translation
from capyc.rest_framework.exceptions import ValidationException
from circuitbreaker import CircuitBreakerError
from django.core.validators import URLValidator
from django.db.models import Count, Q
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect, render
from django.views.decorators.clickjacking import xframe_options_exempt
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from slugify import slugify

from breathecode.admissions.models import Academy
from breathecode.authenticate.actions import get_user_language
from breathecode.authenticate.models import ProfileAcademy
from breathecode.notify.actions import send_email_message
from breathecode.registry.permissions.consumers import asset_by_slug
from breathecode.services.seo import SEOAnalyzer
from breathecode.utils import GenerateLookupsMixin, capable_of, consume
from breathecode.utils.api_view_extensions.api_view_extensions import APIViewExtensions
from breathecode.utils.views import render_message

from .actions import (
    AssetThumbnailGenerator,
    clean_asset_readme,
    pull_from_github,
    push_to_github,
    scan_asset_originality,
    test_asset,
)
from .caches import AssetCache, AssetCommentCache, CategoryCache, ContentVariableCache, KeywordCache, TechnologyCache
from .models import (
    Asset,
    AssetAlias,
    AssetCategory,
    AssetComment,
    AssetContext,
    AssetErrorLog,
    AssetImage,
    AssetKeyword,
    AssetTechnology,
    ContentVariable,
    KeywordCluster,
    OriginalityScan,
    SEOReport,
)
from .serializers import (
    AcademyAssetSerializer,
    AcademyCommentSerializer,
    AssetAliasSerializer,
    AssetBigAndTechnologyPublishedSerializer,
    AssetBigSerializer,
    AssetBigTechnologySerializer,
    AssetCategorySerializer,
    AssetContextSerializer,
    AssetExpandableSerializer,
    AssetImageSmallSerializer,
    AssetKeywordBigSerializer,
    AssetKeywordSerializer,
    AssetMidSerializer,
    AssetPUTSerializer,
    AssetSerializer,
    AssetTechnologySerializer,
    AssetTinySerializer,
    KeywordClusterBigSerializer,
    KeywordClusterMidSerializer,
    KeywordSmallSerializer,
    OriginalityScanSerializer,
    PostAssetCommentSerializer,
    PostAssetSerializer,
    POSTCategorySerializer,
    PostKeywordClusterSerializer,
    PostKeywordSerializer,
    PutAssetCommentSerializer,
    PUTCategorySerializer,
    PUTKeywordSerializer,
    SEOReportSerializer,
    TechnologyPUTSerializer,
    VariableSmallSerializer,
)
from .tasks import async_build_asset_context, async_pull_from_github
from .utils import is_url

logger = logging.getLogger(__name__)

SYSTEM_EMAIL = os.getenv("SYSTEM_EMAIL", None)
ENV = os.getenv("ENV", "development")


@api_view(["GET"])
@permission_classes([AllowAny])
def forward_asset_url(request, asset_slug=None):

    asset = Asset.get_by_slug(asset_slug, request)
    if asset is None:
        return render_message(request, f"Asset with slug {asset_slug} not found")

    validator = URLValidator()
    try:

        if not asset.external and asset.asset_type == "LESSON":
            slug = Path(asset.readme_url).stem
            url = "https://4geeks.com/en/lesson/" + slug + "?plain=true"

            if ENV == "development":
                return render_message(request, "Redirect to: " + url, academy=asset.academy)
            else:
                return HttpResponseRedirect(redirect_to=url)

        validator(asset.url)
        if asset.gitpod:
            return HttpResponseRedirect(redirect_to="https://gitpod.io#" + asset.url)
        else:
            return HttpResponseRedirect(redirect_to=asset.url)
    except Exception as e:
        logger.error(e)
        msg = f"The url for the {asset.asset_type.lower()} your are trying to open ({asset_slug}) was not found, this error has been reported and will be fixed soon."
        AssetErrorLog(
            slug=AssetErrorLog.INVALID_URL, path=asset_slug, asset=asset, asset_type=asset.asset_type, status_text=msg
        ).save()

        return render_message(request, msg, academy=asset.academy)


@api_view(["GET"])
@permission_classes([AllowAny])
@xframe_options_exempt
def render_preview_html(request, asset_slug):
    asset = Asset.get_by_slug(asset_slug, request)
    if asset is None:
        return render_message(request, f"Asset with slug {asset_slug} not found")

    if asset.asset_type == "QUIZ":
        return render_message(request, "Quiz cannot be previewed", academy=asset.academy)

    readme = asset.get_readme(parse=True)
    response = render(
        request,
        readme["frontmatter"]["format"] + ".html",
        {
            **AssetBigSerializer(asset).data,
            "html": readme["html"],
            "theme": request.GET.get("theme", "light"),
            "plain": request.GET.get("plain", "false"),
            "styles": readme["frontmatter"]["inlining"]["css"][0] if "inlining" in readme["frontmatter"] else None,
            "frontmatter": readme["frontmatter"].items(),
        },
    )

    # Set Content-Security-Policy header
    response["Content-Security-Policy"] = "frame-ancestors 'self' https://4geeks.com"

    return response


# Create your views here.


class TechnologyView(APIView):
    """
    View to retrieve a list of technologies or a specific technology by slug.
    """

    permission_classes = [AllowAny]
    extensions = APIViewExtensions(cache=TechnologyCache, paginate=True, sort="sort_priority")

    def get(self, request, tech_slug=None):
        lang = request.GET.get("lang", "en")
        if lang == "en":
            lang = "us"

        handler = self.extensions(request)
        cache = handler.cache.get()
        if cache is not None:
            return cache

        if tech_slug:
            try:
                technology = AssetTechnology.objects.get(slug=tech_slug)
            except AssetTechnology.DoesNotExist:
                raise ValidationException(f"Technology with slug '{tech_slug}' not found", code=404)
            serializer = AssetBigTechnologySerializer(technology)
            return Response(serializer.data)

        items = AssetTechnology.objects.filter(parent__isnull=True)

        if "sort_priority" in request.GET:
            try:
                param = int(request.GET.get("sort_priority"))
                items = items.filter(sort_priority__exact=param)
            except ValueError:
                raise ValidationException(
                    translation(
                        lang,
                        en="The parameter must be an integer, nothing else",
                        es="El parametró debera ser un entero y nada mas ",
                        slug="integer-not-found",
                    )
                )

        if "lang" in request.GET:
            param = request.GET.get("lang")
            items = items.filter(Q(lang__iexact=param) | Q(lang="") | Q(lang__isnull=True))

        if "is_deprecated" not in request.GET or request.GET.get("is_deprecated").lower() == "false":
            items = items.filter(is_deprecated=False)

        like = request.GET.get("like", None)
        if like and like not in ["undefined", ""]:
            items = items.filter(Q(slug__icontains=like) | Q(title__icontains=like))

        if "visibility" in request.GET:
            visibility_param = request.GET.get("visibility")
            items = items.filter(visibility__iexact=visibility_param)

        items = handler.queryset(items)

        serializer = AssetTechnologySerializer(items, many=True)
        return handler.response(serializer.data)


class AcademyTechnologyView(APIView, GenerateLookupsMixin):
    """
    List all snippets, or create a new snippet.
    """

    extensions = APIViewExtensions(cache=TechnologyCache, sort="-slug", paginate=True)

    def _has_valid_parent(self):
        regex = r"^(?:\d+,)*(?:\d+)$"
        return bool(re.findall(regex, self.request.GET.get("parent", "")))

    @capable_of("read_technology")
    def get(self, request, academy_id=None):
        lang = get_user_language(request)
        handler = self.extensions(request)
        cache = handler.cache.get()
        if cache is not None:
            return cache

        items = AssetTechnology.objects.all()
        lookup = {}

        has_valid_parent = self._has_valid_parent()
        if self.request.GET.get("include_children") != "true" and not has_valid_parent:
            items = items.filter(parent__isnull=True)

        if "language" in self.request.GET or "lang" in self.request.GET:
            param = self.request.GET.get("language", "")
            if not param:
                param = self.request.GET.get("lang")

            if param == "en":
                param = "us"
            items = items.filter(Q(lang__iexact=param) | Q(lang="") | Q(lang__isnull=True))

        if "sort_priority" in self.request.GET:
            param = self.request.GET.get("sort_priority")
            try:
                param = int(param)

                lookup["sort_priority__iexact"] = param

            except Exception:
                raise ValidationException(
                    translation(
                        lang,
                        en="The parameter must be an integer",
                        es="El parametró debe ser un entero",
                        slug="not-an-integer",
                    )
                )

        if "visibility" in self.request.GET:
            param = self.request.GET.get("visibility")
            lookup["visibility__in"] = [p.upper() for p in param.split(",")]
        else:
            lookup["visibility"] = "PUBLIC"

        if has_valid_parent:
            param = self.request.GET.get("parent")
            lookup["parent__id__in"] = [int(p) for p in param.split(",")]

        like = request.GET.get("like", None)
        if like is not None and like != "undefined" and like != "":
            items = items.filter(Q(slug__icontains=slugify(like)) | Q(title__icontains=like))

        if slug := request.GET.get("slug"):
            lookup["slug__in"] = slug.split(",")

        if asset_slug := request.GET.get("asset_slug"):
            lookup["featured_asset__slug__in"] = asset_slug.split(",")

        if asset_type := request.GET.get("asset_type"):
            lookup["featured_asset__asset_type__in"] = asset_type.split(",")

        if "is_deprecated" not in request.GET or request.GET.get("is_deprecated").lower() == "false":
            lookup["is_deprecated"] = False

        items = items.filter(**lookup).order_by("sort_priority")
        items = handler.queryset(items)

        serializer = AssetBigTechnologySerializer(items, many=True)

        return handler.response(serializer.data)

    @capable_of("crud_technology")
    def put(self, request, tech_slug=None, academy_id=None):

        lookups = self.generate_lookups(request, many_fields=["slug"])

        if lookups and tech_slug:
            raise ValidationException(
                "user_id or cohort_id was provided in url " "in bulk mode request, use querystring style instead",
                code=400,
            )

        if "slug" not in request.GET and tech_slug is None:
            raise ValidationException("Missing technology slug(s)")
        elif tech_slug is not None:
            lookups["slug__in"] = [tech_slug]

        techs = AssetTechnology.objects.filter(**lookups).order_by("sort_priority")
        _count = techs.count()
        if _count == 0:
            raise ValidationException("This technolog(ies) does not exist for this academy", 404)

        serializers = []
        for t in techs:
            serializer = TechnologyPUTSerializer(
                t, data=request.data, many=False, context={"request": request, "academy_id": academy_id}
            )
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            serializers.append(serializer)

        resp = []
        for s in serializers:
            tech = s.save()
            resp.append(AssetBigTechnologySerializer(tech, many=False).data)

        if tech_slug is not None:
            return Response(resp.pop(), status=status.HTTP_200_OK)
        else:
            return Response(resp, status=status.HTTP_200_OK)


@api_view(["GET"])
def get_categories(request):
    items = AssetCategory.objects.filter(visibility="PUBLIC")
    serializer = AssetCategorySerializer(items, many=True)
    return Response(serializer.data)


@api_view(["GET"])
def get_keywords(request):
    items = AssetKeyword.objects.all()
    serializer = AssetKeywordSerializer(items, many=True)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([AllowAny])
def get_translations(request):
    langs = Asset.objects.all().values_list("lang", flat=True)
    langs = set(langs)

    return Response([{"slug": l, "title": l} for l in langs])


@api_view(["POST"])
@permission_classes([AllowAny])
def handle_test_asset(request):
    test_asset(request.data)
    return Response({"status": "ok"})


@api_view(["GET"])
@permission_classes([AllowAny])
@xframe_options_exempt
def render_readme(request, asset_slug, extension="raw"):

    asset = Asset.get_by_slug(asset_slug, request)
    if asset is None:
        raise ValidationException(f"Asset {asset_slug} not found", status.HTTP_404_NOT_FOUND)

    response = HttpResponse("Invalid extension format", content_type="text/html")
    if extension == "raw":
        readme = asset.get_readme()
        response = HttpResponse(readme["decoded_raw"], content_type="text/markdown")

    if extension == "html":
        if asset.html is not None and asset.html != "":
            response = HttpResponse(asset.html, content_type="text/html")
        else:
            asset.log_error(
                AssetErrorLog.EMPTY_HTML, status_text="Someone requested the asset HTML via API and it was empty"
            )
            readme = asset.get_readme(parse=True, remove_frontmatter=request.GET.get("frontmatter", "true") != "false")
            asset.html = readme["html"]
            asset.save()
            response = HttpResponse(readme["html"], content_type="text/html")

    elif extension in ["md", "mdx", "txt"]:
        readme = asset.get_readme(parse=True, remove_frontmatter=request.GET.get("frontmatter", "true") != "false")
        response = HttpResponse(readme["decoded"], content_type="text/markdown")

    elif extension == "ipynb":
        readme = asset.get_readme()
        response = HttpResponse(readme["decoded"], content_type="application/json")

    return response


@api_view(["GET"])
@permission_classes([AllowAny])
def get_alias_redirects(request):
    aliases = AssetAlias.objects.all()
    redirects = {}

    if "academy" in request.GET:
        param = request.GET.get("academy", "")
        aliases = aliases.filter(asset__academy__id__in=param.split(","))

    for a in aliases:
        if a.slug != a.asset.slug:
            redirects[a.slug] = {"slug": a.asset.slug, "type": a.asset.asset_type, "lang": a.asset.lang}

    return Response(redirects)


@api_view(["GET"])
@permission_classes([AllowAny])
def get_config(request, asset_slug):
    asset = Asset.get_by_slug(asset_slug, request)
    if asset is None:
        raise ValidationException(f"Asset not {asset_slug} found", status.HTTP_404_NOT_FOUND)

    main_branch = "master"
    response = requests.head(f"{asset.url}/tree/{main_branch}", allow_redirects=False, timeout=2)
    if response.status_code == 302:
        main_branch = "main"

    try:
        response = requests.get(f"{asset.url}/blob/{main_branch}/learn.json?raw=true", timeout=2)
        if response.status_code == 404:
            response = requests.get(f"{asset.url}/blob/{main_branch}/bc.json?raw=true", timeout=2)
            if response.status_code == 404:
                raise ValidationException(f"Config file not found for {asset.url}", code=404, slug="config_not_found")

        return Response(response.json())
    except Exception:
        data = {
            "MESSAGE": f"learn.json or bc.json not found or invalid for for: \n {asset.url}",
            "TITLE": f"Error fetching the exercise meta-data learn.json for {asset.asset_type.lower()} {asset.slug}",
        }

        to = SYSTEM_EMAIL
        if asset.author is not None:
            to = asset.author.email

        send_email_message("message", to=to, data=data, academy=asset.academy)
        raise ValidationException(
            f"Config file invalid or not found for {asset.url}", code=404, slug="config_not_found"
        )


class AssetThumbnailView(APIView):
    """
    get:
        Get asset thumbnail.
    """

    permission_classes = [AllowAny]

    def get(self, request, asset_slug):
        width = int(request.GET.get("width", "0"))
        height = int(request.GET.get("height", "0"))

        asset = Asset.objects.filter(slug=asset_slug).first()
        generator = AssetThumbnailGenerator(asset, width, height)

        url, permanent = generator.get_thumbnail_url()
        return redirect(url, permanent=permanent)

    # this method will force to reset the thumbnail
    @capable_of("crud_asset")
    def post(self, request, asset_slug, academy_id):
        lang = get_user_language(request)

        width = int(request.GET.get("width", "0"))
        height = int(request.GET.get("height", "0"))

        asset = Asset.objects.filter(slug=asset_slug, academy__id=academy_id).first()
        if asset is None:
            raise ValidationException(
                f"Asset with slug {asset_slug} not found for this academy", slug="asset-slug-not-found", code=400
            )

        generator = AssetThumbnailGenerator(asset, width, height)

        # wait one second
        try:
            asset = generator.create(delay=1500)

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

        serializer = AcademyAssetSerializer(asset)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AcademyContentVariableView(APIView):
    """
    get:
        Get content variables thumbnail.
    """

    extensions = APIViewExtensions(cache=ContentVariableCache, paginate=True)

    @capable_of("read_content_variables")
    def get(self, request, academy_id, variable_slug=None):
        handler = self.extensions(request)

        if variable_slug is not None:
            variable = ContentVariable.objects.filter(slug=variable_slug).first()
            if variable is None:
                raise ValidationException(
                    f"Variable {variable_slug} not found for this academy", status.HTTP_404_NOT_FOUND
                )

            serializer = VariableSmallSerializer(variable)
            return handler.response(serializer.data)

        items = ContentVariable.objects.filter(academy__id=academy_id)
        lookup = {}

        if "lang" in self.request.GET:
            param = self.request.GET.get("lang")
            lookup["lang"] = param

        items = items.filter(**lookup)
        items = handler.queryset(items)

        serializer = VariableSmallSerializer(items, many=True)

        return handler.response(serializer.data)

    # this method will force to reset the thumbnail
    @capable_of("crud_asset")
    def post(self, request, asset_slug, academy_id):
        lang = get_user_language(request)

        width = int(request.GET.get("width", "0"))
        height = int(request.GET.get("height", "0"))

        asset = Asset.objects.filter(slug=asset_slug, academy__id=academy_id).first()
        if asset is None:
            raise ValidationException(
                f"Asset with slug {asset_slug} not found for this academy", slug="asset-slug-not-found", code=400
            )

        generator = AssetThumbnailGenerator(asset, width, height)

        # wait one second
        try:
            asset = generator.create(delay=1500)

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

        serializer = AcademyAssetSerializer(asset)
        return Response(serializer.data, status=status.HTTP_200_OK)


# Create your views here.
class AssetView(APIView, GenerateLookupsMixin):
    """
    List all snippets, or create a new snippet.
    """

    permission_classes = [AllowAny]
    extensions = APIViewExtensions(cache=AssetCache, sort="-published_at", paginate=True)

    def get(self, request, asset_slug=None):
        handler = self.extensions(request)

        cache = handler.cache.get()
        if cache is not None:
            return cache

        lang = get_user_language(request)

        if asset_slug is not None:
            asset = Asset.get_by_slug(asset_slug, request)
            if asset is None:
                raise ValidationException(f"Asset {asset_slug} not found", status.HTTP_404_NOT_FOUND)

            serializer = AssetBigAndTechnologyPublishedSerializer(asset)
            return handler.response(serializer.data)

        items = Asset.objects.all()
        lookup = {}
        query = handler.lookup.build(
            lang,
            strings={
                "iexact": [
                    "test_status",
                    "sync_status",
                ],
                "in": [
                    "difficulty",
                    "status",
                    "asset_type",
                    "category__slug",
                    "technologies__slug",
                    "seo_keywords__slug",
                ],
            },
            ids=["author", "owner"],
            bools={
                "exact": ["with_video", "interactive", "graded"],
            },
            overwrite={
                "category": "category__slug",
                "technologies": "technologies__slug",
                "seo_keywords": "seo_keywords__slug",
            },
        )

        like = request.GET.get("like", None)
        if like is not None:
            if is_url(like):
                items = items.filter(Q(readme_url__icontains=like) | Q(url__icontains=like))
            else:
                items = items.filter(
                    Q(slug__icontains=slugify(like))
                    | Q(title__icontains=like)
                    | Q(assetalias__slug__icontains=slugify(like))
                )

        if "slug" in self.request.GET:
            asset_type = self.request.GET.get("asset_type", None)
            param = self.request.GET.get("slug")
            asset = Asset.get_by_slug(param, request, asset_type=asset_type)
            if asset is not None:
                lookup["slug"] = asset.slug
            else:
                lookup["slug"] = param

        if "language" in self.request.GET:
            param = self.request.GET.get("language")
            if param == "en":
                param = "us"
            lookup["lang"] = param

        if "status" not in self.request.GET:
            lookup["status__in"] = ["PUBLISHED"]

        try:
            if "academy" in self.request.GET and self.request.GET.get("academy") not in ["null", ""]:
                param = self.request.GET.get("academy")
                lookup["academy__in"] = [int(p) for p in param.split(",")]
        except Exception:
            raise ValidationException(
                translation(
                    lang,
                    en="The academy filter value should be an integer",
                    es="El valor del filtro de academy debería ser un entero",
                    slug="academy-id-must-be-integer",
                ),
                code=400,
            )

        if "video" in self.request.GET:
            param = self.request.GET.get("video")
            if param == "true":
                lookup["with_video"] = True

        lookup["external"] = False
        if "external" in self.request.GET:
            param = self.request.GET.get("external")
            if param == "true":
                lookup["external"] = True
            elif param == "both":
                lookup.pop("external", None)

        need_translation = self.request.GET.get("need_translation", False)
        if need_translation == "true":
            items = items.annotate(num_translations=Count("all_translations")).filter(num_translations__lte=1)

        if "exclude_category" in self.request.GET:
            param = self.request.GET.get("exclude_category")
            items = items.exclude(category__slug__in=[p for p in param.split(",") if p])

        if "authors_username" in self.request.GET:
            au = self.request.GET.get("authors_username", "").split(",")
            query = Q()
            for username in au:
                query |= Q(authors_username__icontains=username)
            items = items.exclude(~query)

        items = items.filter(query, **lookup, visibility="PUBLIC").distinct()
        items = handler.queryset(items)

        expand = self.request.GET.get("expand")

        if "big" in self.request.GET:
            serializer = AssetMidSerializer(items, many=True)
        elif expand is not None:
            serializer = AssetExpandableSerializer(items, many=True, expand=expand.split(","))
        else:
            serializer = AssetSerializer(items, many=True)

        return handler.response(serializer.data)


class AssetContextView(APIView, GenerateLookupsMixin):
    """
    List all snippets, or create a new snippet.
    """

    permission_classes = [AllowAny]
    extensions = APIViewExtensions(cache=AssetCache, paginate=True)

    def get(self, request, asset_id=None):
        handler = self.extensions(request)

        cache = handler.cache.get()
        if cache is not None:
            return cache

        asset_context = AssetContext.objects.filter(asset__id=asset_id).first()
        if asset_context is None:
            asset = Asset.objects.filter(id=asset_id).first()
            if asset is None:
                raise ValidationException(
                    f"Asset {asset_id} not found", status.HTTP_404_NOT_FOUND, slug="asset-not-found"
                )
            asset_context = AssetContext(
                asset=asset,
                status="PROCESSING",
                status_text="The asset context is being generated in the background and will be ready in a moment.",
            )
            asset_context.save()
            async_build_asset_context.delay(asset_id)

        serializer = AssetContextSerializer(asset_context, many=False)

        return handler.response(serializer.data)


# Create your views here.
class AcademyAssetActionView(APIView):
    """
    List all snippets, or create a new snippet.
    """

    @capable_of("crud_asset")
    def put(self, request, asset_slug, action_slug, academy_id=None):

        if asset_slug is None:
            raise ValidationException("Missing asset_slug")

        asset = Asset.objects.filter(slug__iexact=asset_slug, academy__id=academy_id).first()
        if asset is None:
            raise ValidationException(f"This asset {asset_slug} does not exist for this academy {academy_id}", 404)

        possible_actions = ["test", "pull", "push", "analyze_seo", "clean", "originality"]
        if action_slug not in possible_actions:
            raise ValidationException(f"Invalid action {action_slug}")
        try:
            if action_slug == "test":
                test_asset(asset)
            elif action_slug == "clean":
                clean_asset_readme(asset)
            elif action_slug == "pull":
                override_meta = False
                if request.data and "override_meta" in request.data:
                    override_meta = request.data["override_meta"]
                pull_from_github(asset.slug, override_meta=override_meta)
            elif action_slug == "push":
                if asset.asset_type not in ["ARTICLE", "LESSON", "QUIZ"]:
                    raise ValidationException(
                        f"Asset type {asset.asset_type} cannot be pushed to GitHub, please update the Github repository manually"
                    )

                push_to_github(asset.slug, author=request.user)
            elif action_slug == "analyze_seo":
                report = SEOAnalyzer(asset)
                report.start()
            elif action_slug == "originality":

                if asset.asset_type not in ["ARTICLE", "LESSON"]:
                    raise ValidationException("Only lessons and articles can be scanned for originality")
                scan_asset_originality(asset)

        except Exception as e:
            logger.exception(e)
            if isinstance(e, Exception):
                raise ValidationException(str(e))

            raise ValidationException(
                "; ".join([k.capitalize() + ": " + "".join(v) for k, v in e.message_dict.items()])
            )

        asset = Asset.objects.filter(slug=asset_slug, academy__id=academy_id).first()
        serializer = AcademyAssetSerializer(asset)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @capable_of("crud_asset")
    def post(self, request, action_slug, academy_id=None):
        if action_slug not in ["test", "pull", "push", "analyze_seo"]:
            raise ValidationException(f"Invalid action {action_slug}")

        if not request.data["assets"]:
            raise ValidationException("Assets not found in the body of the request.")

        assets = request.data["assets"]

        if len(assets) < 1:
            raise ValidationException("The list of Assets is empty.")

        invalid_assets = []

        for asset_slug in assets:
            asset = Asset.objects.filter(slug__iexact=asset_slug, academy__id=academy_id).first()
            if asset is None:
                invalid_assets.append(asset_slug)
                continue
            try:
                if action_slug == "test":
                    test_asset(asset)
                elif action_slug == "clean":
                    clean_asset_readme(asset)
                elif action_slug == "pull":
                    override_meta = False
                    if request.data and "override_meta" in request.data:
                        override_meta = request.data["override_meta"]
                    pull_from_github(asset.slug, override_meta=override_meta)
                elif action_slug == "push":
                    if asset.asset_type not in ["ARTICLE", "LESSON"]:
                        raise ValidationException(
                            "Only lessons and articles and be pushed to github, please update the Github repository yourself and come back to pull the changes from here"
                        )

                    push_to_github(asset.slug, author=request.user)
                elif action_slug == "analyze_seo":
                    report = SEOAnalyzer(asset)
                    report.start()

            except Exception as e:
                logger.exception(e)
                invalid_assets.append(asset_slug)
                pass

        pulled_assets = list(set(assets).difference(set(invalid_assets)))

        if len(pulled_assets) < 1:
            raise ValidationException(f"Failed to {action_slug} for these assets: {invalid_assets}")

        return Response(
            f'These asset readmes were pulled correctly from GitHub: {pulled_assets}. {f"These assets {invalid_assets} do not exist for this academy {academy_id}" if len(invalid_assets) > 0 else ""}',
            status=status.HTTP_200_OK,
        )


# Create your views here.
class AcademyAssetSEOReportView(APIView, GenerateLookupsMixin):
    """
    List all snippets, or create a new snippet.
    """

    extensions = APIViewExtensions(sort="-created_at", paginate=True)

    @capable_of("read_asset")
    def get(self, request, asset_slug, academy_id):

        handler = self.extensions(request)

        reports = SEOReport.objects.filter(asset__slug=asset_slug)
        if reports.count() == 0:
            raise ValidationException(f"No report found for asset {asset_slug}", status.HTTP_404_NOT_FOUND)

        reports = handler.queryset(reports)
        serializer = SEOReportSerializer(reports, many=True)
        return handler.response(serializer.data)


# Create your views here.
class AcademyAssetOriginalityView(APIView, GenerateLookupsMixin):
    """
    List all snippets, or create a new snippet.
    """

    extensions = APIViewExtensions(sort="-created_at", paginate=True)

    @capable_of("read_asset")
    def get(self, request, asset_slug, academy_id):

        handler = self.extensions(request)

        scans = OriginalityScan.objects.filter(asset__slug=asset_slug)
        if scans.count() == 0:
            raise ValidationException(f"No originality scans found for asset {asset_slug}", status.HTTP_404_NOT_FOUND)

        scans = scans.order_by("-created_at")

        scans = handler.queryset(scans)
        serializer = OriginalityScanSerializer(scans, many=True)
        return handler.response(serializer.data)


class AssetSupersedesView(APIView, GenerateLookupsMixin):
    """
    List all snippets, or create a new snippet.
    """

    @capable_of("read_asset")
    def get(self, request, asset_slug=None, academy_id=None):

        asset = Asset.get_by_slug(asset_slug, request)

        supersedes = []
        _aux = asset
        while _aux.superseded_by is not None:
            supersedes.append(_aux.superseded_by)
            _aux = _aux.superseded_by

        previous = []
        _aux = asset
        try:
            while _aux.previous_version is not None:
                previous.append(_aux.previous_version)
                _aux = _aux.previous_version
        except Exception:
            pass

        return Response(
            {
                "supersedes": AssetTinySerializer(supersedes, many=True).data,
                "previous": AssetTinySerializer(previous, many=True).data,
            }
        )


class AcademyAssetView(APIView, GenerateLookupsMixin):
    """
    List all snippets, or create a new snippet.
    """

    extensions = APIViewExtensions(cache=AssetCache, sort="-published_at", paginate=True)

    @capable_of("read_asset")
    def get(self, request, asset_slug=None, academy_id=None):
        handler = self.extensions(request)

        cache = handler.cache.get()
        if cache is not None:
            return cache

        member = ProfileAcademy.objects.filter(user=request.user, academy__id=academy_id).first()
        if member is None:
            raise ValidationException("You don't belong to this academy", status.HTTP_400_BAD_REQUEST)

        if asset_slug is not None:
            asset = Asset.get_by_slug(asset_slug, request)
            if asset is None or (asset.academy is not None and asset.academy.id != int(academy_id)):
                raise ValidationException(f"Asset {asset_slug} not found for this academy", status.HTTP_404_NOT_FOUND)

            serializer = AcademyAssetSerializer(asset)
            return handler.response(serializer.data)

        items = Asset.objects.filter(Q(academy__id=academy_id) | Q(academy__isnull=True))

        lookup = {}

        if member.role.slug == "content_writer":
            items = items.filter(author__id=request.user.id)
        elif "author" in self.request.GET:
            param = self.request.GET.get("author")
            lookup["author__id"] = param

        if "owner" in self.request.GET:
            param = self.request.GET.get("owner")
            lookup["owner__id"] = param

        like = request.GET.get("like", None)
        if like is not None:
            if is_url(like):
                items = items.filter(Q(readme_url__icontains=like) | Q(url__icontains=like))
            else:
                items = items.filter(
                    Q(slug__icontains=slugify(like))
                    | Q(title__icontains=like)
                    | Q(assetalias__slug__icontains=slugify(like))
                )

        if "asset_type" in self.request.GET:
            param = self.request.GET.get("asset_type")
            lookup["asset_type__iexact"] = param

        if "category" in self.request.GET:
            param = self.request.GET.get("category")
            lookup["category__slug__in"] = [p.lower() for p in param.split(",")]

        if "test_status" in self.request.GET:
            param = self.request.GET.get("test_status")
            lookup["test_status"] = param.upper()

        if "sync_status" in self.request.GET:
            param = self.request.GET.get("sync_status")
            lookup["sync_status"] = param.upper()

        if "slug" in self.request.GET:
            asset_type = self.request.GET.get("asset_type", None)
            param = self.request.GET.get("slug")
            asset = Asset.get_by_slug(param, request, asset_type=asset_type)
            if asset is not None:
                lookup["slug"] = asset.slug
            else:
                lookup["slug"] = param

        if "language" in self.request.GET or "lang" in self.request.GET:
            param = self.request.GET.get("language")
            if not param:
                param = self.request.GET.get("lang")

            if param == "en":
                param = "us"
            lookup["lang"] = param

        if "visibility" in self.request.GET:
            param = self.request.GET.get("visibility")
            lookup["visibility__in"] = [p.upper() for p in param.split(",")]
        else:
            lookup["visibility"] = "PUBLIC"

        if "technologies" in self.request.GET:
            param = self.request.GET.get("technologies")
            lookup["technologies__slug__in"] = [p.lower() for p in param.split(",")]

        if "keywords" in self.request.GET:
            param = self.request.GET.get("keywords")
            items = items.filter(seo_keywords__slug__in=[p.lower() for p in param.split(",")])

        if "status" in self.request.GET:
            param = self.request.GET.get("status")
            lookup["status__in"] = [p.upper() for p in param.split(",")]
        else:
            items = items.exclude(status="DELETED")

        if "sync_status" in self.request.GET:
            param = self.request.GET.get("sync_status")
            lookup["sync_status__in"] = [p.upper() for p in param.split(",")]

        if "video" in self.request.GET:
            param = self.request.GET.get("video")
            if param == "true":
                lookup["with_video"] = True

        if "interactive" in self.request.GET:
            param = self.request.GET.get("interactive")
            if param == "true":
                lookup["interactive"] = True

        if "graded" in self.request.GET:
            param = self.request.GET.get("graded")
            if param == "true":
                lookup["graded"] = True

        lookup["external"] = False
        if "external" in self.request.GET:
            param = self.request.GET.get("external")
            if param == "true":
                lookup["external"] = True
            elif param == "both":
                lookup.pop("external", None)

        if "superseded_by" in self.request.GET:
            param = self.request.GET.get("superseded_by")
            if param.lower() in ["none", "null"]:
                lookup["superseded_by__isnull"] = True
            else:
                if param.isnumeric():
                    lookup["superseded_by__id"] = param
                else:
                    lookup["superseded_by__slug"] = param

        if "previous_version" in self.request.GET:
            param = self.request.GET.get("previous_version")
            if param.lower() in ["none", "null"]:
                lookup["previous_version__isnull"] = True
            else:
                if param.isnumeric():
                    lookup["previous_version__id"] = param
                else:
                    lookup["previous_version__slug"] = param

        published_before = request.GET.get("published_before", "")
        if published_before != "":
            items = items.filter(published_at__lte=published_before)

        published_after = request.GET.get("published_after", "")
        if published_after != "":
            items = items.filter(published_at__gte=published_after)

        need_translation = self.request.GET.get("need_translation", False)
        if need_translation == "true":
            items = items.annotate(num_translations=Count("all_translations")).filter(num_translations__lte=1)

        items = items.filter(**lookup).distinct()
        items = handler.queryset(items)

        serializer = AcademyAssetSerializer(items, many=True)

        return handler.response(serializer.data)

    @capable_of("crud_asset")
    def put(self, request, asset_slug=None, academy_id=None):

        data_list = request.data
        if not isinstance(request.data, list):

            # make it a list
            data_list = [request.data]

            if asset_slug is None:
                raise ValidationException("Missing asset_slug")

            asset = Asset.objects.filter(slug__iexact=asset_slug, academy__id=academy_id).first()
            if asset is None:
                raise ValidationException(f"This asset {asset_slug} does not exist for this academy {academy_id}", 404)

            data_list[0]["id"] = asset.id

        all_assets = []
        for data in data_list:

            if "technologies" in data and len(data["technologies"]) > 0 and isinstance(data["technologies"][0], str):
                technology_ids = AssetTechnology.objects.filter(slug__in=data["technologies"]).values_list(
                    "pk", flat=True
                )
                delta = len(data["technologies"]) - len(technology_ids)
                if delta != 0:
                    raise ValidationException(f"{delta} of the assigned technologies for this lesson are not found")

                data["technologies"] = technology_ids

            if "seo_keywords" in data and len(data["seo_keywords"]) > 0:
                if isinstance(data["seo_keywords"][0], str):
                    data["seo_keywords"] = AssetKeyword.objects.filter(slug__in=data["seo_keywords"]).values_list(
                        "pk", flat=True
                    )

            if (
                "all_translations" in data
                and len(data["all_translations"]) > 0
                and isinstance(data["all_translations"][0], str)
            ):
                data["all_translations"] = Asset.objects.filter(slug__in=data["all_translations"]).values_list(
                    "pk", flat=True
                )

            if "id" not in data:
                raise ValidationException("Cannot determine asset id", slug="without-id")

            instance = Asset.objects.filter(id=data["id"], academy__id=academy_id).first()
            if not instance:
                raise ValidationException(
                    f'Asset({data["id"]}) does not exist on this academy', code=404, slug="not-found"
                )
            all_assets.append(instance)

        all_serializers = []
        index = -1
        for data in data_list:
            index += 1
            serializer = AssetPUTSerializer(
                all_assets[index], data=data, context={"request": request, "academy_id": academy_id}
            )
            all_serializers.append(serializer)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        all_assets = []
        for serializer in all_serializers:
            all_assets.append(serializer.save())

        if isinstance(request.data, list):
            serializer = AcademyAssetSerializer(all_assets, many=True)
        else:
            serializer = AcademyAssetSerializer(all_assets.pop(), many=False)

        return Response(serializer.data, status=status.HTTP_200_OK)

    @capable_of("crud_asset")
    def post(self, request, academy_id=None):

        data = {
            **request.data,
        }

        if "seo_keywords" in data and len(data["seo_keywords"]) > 0:
            if isinstance(data["seo_keywords"][0], str):
                data["seo_keywords"] = AssetKeyword.objects.filter(slug__in=data["seo_keywords"]).values_list(
                    "pk", flat=True
                )

        if (
            "all_translations" in data
            and len(data["all_translations"]) > 0
            and isinstance(data["all_translations"][0], str)
        ):
            data["all_translations"] = Asset.objects.filter(slug__in=data["all_translations"]).values_list(
                "pk", flat=True
            )

        if "technologies" in data and len(data["technologies"]) > 0 and isinstance(data["technologies"][0], str):
            technology_ids = (
                AssetTechnology.objects.filter(slug__in=data["technologies"])
                .values_list("pk", flat=True)
                .order_by("sort_priority")
            )
            delta = len(data["technologies"]) - len(technology_ids)
            if delta != 0:
                raise ValidationException(f"{delta} of the assigned technologies for this asset are not found")

            data["technologies"] = technology_ids

        serializer = PostAssetSerializer(data=data, context={"request": request, "academy": academy_id})
        if serializer.is_valid():
            instance = serializer.save()
            async_pull_from_github.delay(instance.slug)
            return Response(AssetBigSerializer(instance).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class V2AcademyAssetView(APIView):
    """
    List all snippets, or create a new snippet.
    """

    extensions = APIViewExtensions(cache=AssetCache, sort="-published_at", paginate=True)

    @capable_of("read_asset")
    @consume("read_lesson", consumer=asset_by_slug)
    def get(self, request, asset: Asset, academy: Academy):
        serializer = AcademyAssetSerializer(asset)
        return Response(serializer.data)


class AssetImageView(APIView, GenerateLookupsMixin):
    """
    List all snippets, or create a new snippet.
    """

    extensions = APIViewExtensions(sort="-created_at", paginate=True)

    @capable_of("read_asset")
    def get(self, request, academy_id=None):

        handler = self.extensions(request)

        items = AssetImage.objects.filter(assets__academy__id=academy_id)
        lookup = {}

        if "slug" in self.request.GET:
            param = self.request.GET.get("slug")
            lookup["assets__slug__in"] = [p.lower() for p in param.split(",")]

        if "download_status" in self.request.GET:
            param = self.request.GET.get("download_status")
            lookup["download_status__in"] = [p.upper() for p in param.split(",")]

        if "original_url" in self.request.GET:
            param = self.request.GET.get("original_url")
            lookup["original_url"] = param

        items = items.filter(**lookup)
        items = handler.queryset(items)

        serializer = AssetImageSmallSerializer(items, many=True)
        return handler.response(serializer.data)


class AcademyAssetCommentView(APIView, GenerateLookupsMixin):
    """
    List all snippets, or create a new snippet.
    """

    extensions = APIViewExtensions(cache=AssetCommentCache, sort="-created_at", paginate=True)

    @capable_of("read_asset")
    def get(self, request, academy_id=None):

        handler = self.extensions(request)
        cache = handler.cache.get()
        if cache is not None:
            return cache

        items = AssetComment.objects.filter(asset__academy__id=academy_id)
        lookup = {}

        if "asset" in self.request.GET:
            param = self.request.GET.get("asset")
            lookup["asset__slug__in"] = [p.lower() for p in param.split(",")]

        if "resolved" in self.request.GET:
            param = self.request.GET.get("resolved")
            if param == "true":
                lookup["resolved"] = True
            elif param == "false":
                lookup["resolved"] = False

        if "delivered" in self.request.GET:
            param = self.request.GET.get("delivered")
            if param == "true":
                lookup["delivered"] = True
            elif param == "false":
                lookup["delivered"] = False

        if "owner" in self.request.GET:
            param = self.request.GET.get("owner")
            lookup["owner__email"] = param

        if "author" in self.request.GET:
            param = self.request.GET.get("author")
            lookup["author__email"] = param

        items = items.filter(**lookup)
        items = handler.queryset(items)

        serializer = AcademyCommentSerializer(items, many=True)
        return handler.response(serializer.data)

    @capable_of("crud_asset")
    def post(self, request, academy_id=None):

        payload = {**request.data, "author": request.user.id}

        serializer = PostAssetCommentSerializer(data=payload, context={"request": request, "academy": academy_id})
        if serializer.is_valid():
            serializer.save()
            serializer = AcademyCommentSerializer(serializer.instance)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of("crud_asset")
    def put(self, request, comment_id, academy_id=None):

        if comment_id is None:
            raise ValidationException("Missing comment_id")

        comment = AssetComment.objects.filter(id=comment_id, asset__academy__id=academy_id).first()
        if comment is None:
            raise ValidationException("This comment does not exist for this academy", 404)

        data = {**request.data}
        if "status" in request.data and request.data["status"] == "NOT_STARTED":
            data["author"] = None

        serializer = PutAssetCommentSerializer(comment, data=data, context={"request": request, "academy": academy_id})
        if serializer.is_valid():
            serializer.save()
            serializer = AcademyCommentSerializer(serializer.instance)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of("crud_asset")
    def delete(self, request, comment_id=None, academy_id=None):

        if comment_id is None:
            raise ValidationException("Missing comment ID on the URL", 404)

        comment = AssetComment.objects.filter(id=comment_id, asset__academy__id=academy_id).first()
        if comment is None:
            raise ValidationException("This comment does not exist", 404)

        comment.delete()
        return Response(None, status=status.HTTP_204_NO_CONTENT)


class AcademyAssetAliasView(APIView, GenerateLookupsMixin):
    """
    List all snippets, or create a new snippet.
    """

    extensions = APIViewExtensions(sort="-created_at", paginate=True)

    @capable_of("read_asset")
    def get(self, request, alias_slug=None, academy_id=None):

        handler = self.extensions(request)
        # cache = handler.cache.get()
        # if cache is not None:
        #     return cache

        lang = get_user_language(request)

        if alias_slug:
            item = AssetAlias.objects.filter(slug=alias_slug, asset__academy__id=academy_id).first()
            if not item:
                raise ValidationException(
                    translation(
                        lang,
                        en="Asset alias with slug {alias_slug} not found for this academy",
                        es="No se ha encontrado el alias {alias_slug} para esta academia",
                        slug="not-found",
                    )
                )

            serializer = AssetAliasSerializer(item, many=False)
            return handler.response(serializer.data)

        items = AssetAlias.objects.filter(asset__academy__id=academy_id)
        lookup = {}

        if "asset" in self.request.GET:
            param = self.request.GET.get("asset")
            lookup["asset__slug__in"] = [p.lower() for p in param.split(",")]

        items = items.filter(**lookup)
        items = handler.queryset(items)

        serializer = AssetAliasSerializer(items, many=True)
        return handler.response(serializer.data)

    @capable_of("crud_asset")
    def delete(self, request, alias_slug=None, academy_id=None):
        lang = get_user_language(request)
        if not alias_slug:
            raise ValidationException(
                translation(
                    lang,
                    en="Missing alias slug",
                    es="Especifica el slug del alias que deseas eliminar",
                    slug="missing-alias-slug",
                )
            )

        item = AssetAlias.objects.filter(slug=alias_slug, asset__academy__id=academy_id).first()
        if not item:
            raise ValidationException(
                translation(
                    lang,
                    en=f"Asset alias with slug {alias_slug} not found for this academy",
                    es=f"No se ha encontrado el alias {alias_slug} para esta academia",
                    slug="not-found",
                )
            )

        if item.asset.slug == item.slug:
            raise ValidationException(
                translation(
                    lang,
                    en="Rename the asset slug before deleting this alias",
                    es="Necesitas renombrar el slug principal del asset antes de eliminar este alias",
                    slug="rename-asset-slug",
                )
            )

        item.delete()

        return Response(None, status=status.HTTP_204_NO_CONTENT)


class AcademyCategoryView(APIView, GenerateLookupsMixin):
    """
    List all snippets, or create a new snippet.
    """

    extensions = APIViewExtensions(cache=CategoryCache, sort="-created_at", paginate=True)

    @capable_of("read_category")
    def get(self, request, category_slug=None, academy_id=None):

        handler = self.extensions(request)
        cache = handler.cache.get()
        if cache is not None:
            return cache

        items = AssetCategory.objects.filter(academy__id=academy_id)
        lookup = {}

        like = request.GET.get("like", None)
        if like is not None and like != "undefined" and like != "":
            items = items.filter(Q(slug__icontains=slugify(like)) | Q(title__icontains=like))

        lang = request.GET.get("lang", None)
        if lang is not None:
            items = items.filter(lang__iexact=lang)

        items = items.filter(**lookup)
        items = handler.queryset(items)

        serializer = AssetCategorySerializer(items, many=True)
        return handler.response(serializer.data)

    @capable_of("crud_category")
    def post(self, request, academy_id=None):

        data = {**request.data}
        if "lang" in data:
            data["lang"] = data["lang"].upper()

        serializer = POSTCategorySerializer(data=data, context={"request": request, "academy": academy_id})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of("crud_category")
    def put(self, request, category_slug, academy_id=None):

        cat = None
        if category_slug.isnumeric():
            cat = AssetCategory.objects.filter(id=category_slug, academy__id=academy_id).first()
        else:
            cat = AssetCategory.objects.filter(slug=category_slug, academy__id=academy_id).first()

        if cat is None:
            raise ValidationException("This category does not exist for this academy", 404)

        data = {**request.data}
        if "lang" in data:
            data["lang"] = data["lang"].upper()

        serializer = PUTCategorySerializer(cat, data=data, context={"request": request, "academy": academy_id})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of("crud_category")
    def delete(self, request, academy_id=None):
        lookups = self.generate_lookups(request, many_fields=["id"])
        if lookups:
            items = AssetCategory.objects.filter(**lookups, academy__id=academy_id)

            for item in items:
                item.delete()
            return Response(None, status=status.HTTP_204_NO_CONTENT)
        else:
            raise ValidationException("Category ids were not provided", 404, slug="missing_ids")


class AcademyKeywordView(APIView, GenerateLookupsMixin):
    """
    List all snippets, or create a new snippet.
    """

    extensions = APIViewExtensions(cache=KeywordCache, sort="-created_at", paginate=True)

    @capable_of("read_keyword")
    def get(self, request, keyword_slug=None, academy_id=None):

        handler = self.extensions(request)
        cache = handler.cache.get()
        if cache is not None:
            return cache

        items = AssetKeyword.objects.filter(academy__id=academy_id)
        lookup = {}

        if "cluster" in self.request.GET:
            param = self.request.GET.get("cluster")
            if param == "null":
                lookup["cluster"] = None
            else:
                lookup["cluster__slug__in"] = [p.lower() for p in param.split(",")]

        like = request.GET.get("like", None)
        if like is not None and like != "undefined" and like != "":
            items = items.filter(Q(slug__icontains=slugify(like)) | Q(title__icontains=like))

        lang = request.GET.get("lang", None)
        if lang is not None and lang != "undefined" and lang != "":
            lookup["lang__iexact"] = lang

        items = items.filter(**lookup)
        items = handler.queryset(items)

        serializer = KeywordSmallSerializer(items, many=True)
        return handler.response(serializer.data)

    @capable_of("crud_keyword")
    def post(self, request, academy_id=None):

        payload = {**request.data}

        serializer = PostKeywordSerializer(data=payload, context={"request": request, "academy": academy_id})
        if serializer.is_valid():
            serializer.save()
            serializer = AssetKeywordBigSerializer(serializer.instance)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of("crud_keyword")
    def put(self, request, keyword_slug, academy_id=None):

        keywd = AssetKeyword.objects.filter(slug=keyword_slug, academy__id=academy_id).first()
        if keywd is None:
            raise ValidationException("This keyword does not exist for this academy", 404)

        data = {**request.data}

        serializer = PUTKeywordSerializer(keywd, data=data, context={"request": request, "academy": academy_id})
        if serializer.is_valid():
            serializer.save()
            serializer = AssetKeywordBigSerializer(serializer.instance)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of("crud_keyword")
    def delete(self, request, academy_id=None):
        lookups = self.generate_lookups(request, many_fields=["id"])
        if lookups:
            items = AssetKeyword.objects.filter(**lookups, academy__id=academy_id)

            for item in items:
                item.delete()
            return Response(None, status=status.HTTP_204_NO_CONTENT)
        else:
            raise ValidationException("Asset ids were not provided", 404, slug="missing_ids")


class AcademyKeywordClusterView(APIView, GenerateLookupsMixin):
    """
    List all snippets, or create a new snippet.
    """

    extensions = APIViewExtensions(sort="-created_at", paginate=True)

    @capable_of("read_keywordcluster")
    def get(self, request, cluster_slug=None, academy_id=None):

        if cluster_slug is not None:
            item = KeywordCluster.objects.filter(academy__id=academy_id, slug=cluster_slug).first()
            if item is None:
                raise ValidationException(
                    f"Cluster with slug {cluster_slug} not found for this academy",
                    status.HTTP_404_NOT_FOUND,
                    slug="cluster-not-found",
                )
            serializer = KeywordClusterBigSerializer(item)
            return Response(serializer.data, status=status.HTTP_200_OK)

        handler = self.extensions(request)

        # cache has been disabled because I cant get it to refresh then keywords are resigned to assets
        # cache = handler.cache.get()
        # if cache is not None:
        #     return cache

        items = KeywordCluster.objects.filter(academy__id=academy_id)
        lookup = {}

        if "visibility" in self.request.GET:
            param = self.request.GET.get("visibility")
            lookup["visibility"] = param.upper()
        else:
            lookup["visibility"] = "PUBLIC"

        like = request.GET.get("like", None)
        if like is not None and like != "undefined" and like != "":
            items = items.filter(Q(slug__icontains=slugify(like)) | Q(title__icontains=like))

        items = items.filter(**lookup)
        items = handler.queryset(items)

        serializer = KeywordClusterMidSerializer(items, many=True)
        return handler.response(serializer.data)

    @capable_of("crud_keywordcluster")
    def post(self, request, academy_id=None):

        payload = {**request.data, "author": request.user.id}

        serializer = PostKeywordClusterSerializer(data=payload, context={"request": request, "academy": academy_id})
        if serializer.is_valid():
            serializer.save()
            serializer = KeywordClusterBigSerializer(serializer.instance)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of("crud_keywordcluster")
    def put(self, request, cluster_slug, academy_id=None):

        cluster = KeywordCluster.objects.filter(slug=cluster_slug, academy__id=academy_id).first()
        if cluster is None:
            raise ValidationException("This cluster does not exist for this academy", 404)

        data = {**request.data}
        data.pop("academy", False)

        serializer = PostKeywordClusterSerializer(
            cluster, data=data, context={"request": request, "academy": academy_id}
        )
        if serializer.is_valid():
            serializer.save()
            serializer = KeywordClusterBigSerializer(serializer.instance)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of("crud_keywordcluster")
    def delete(self, request, academy_id=None):
        lookups = self.generate_lookups(request, many_fields=["id"])
        if lookups:
            items = KeywordCluster.objects.filter(**lookups, academy__id=academy_id)

            for item in items:
                item.delete()
            return Response(None, status=status.HTTP_204_NO_CONTENT)
        else:
            raise ValidationException("Cluster ids were not provided", 404, slug="missing_ids")
