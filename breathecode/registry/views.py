import requests, logging, os
from pathlib import Path
from django.shortcuts import render
from django.utils import timezone
from django.db.models import Q
from django.http import HttpResponse
from django.core.validators import URLValidator
from .models import Asset, AssetAlias, AssetTechnology, AssetErrorLog
from .actions import test_syllabus, test_asset
from breathecode.notify.actions import send_email_message
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from .serializers import (AssetSerializer, AssetBigSerializer, AssetMidSerializer, AssetTechnologySerializer,
                          PostAssetSerializer)
from breathecode.utils import ValidationException, capable_of
from breathecode.utils.views import private_view, render_message, set_query_parameter
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.views import APIView
from rest_framework import status
from django.http import HttpResponseRedirect
from django.views.decorators.clickjacking import xframe_options_exempt

logger = logging.getLogger(__name__)

SYSTEM_EMAIL = os.getenv('SYSTEM_EMAIL', None)
APP_URL = os.getenv('APP_URL', '')
ENV = os.getenv('ENV', 'development')


@api_view(['GET'])
@permission_classes([AllowAny])
def forward_asset_url(request, asset_slug=None):

    asset = Asset.get_by_slug(asset_slug, request)
    if asset is None:
        return render_message(request, f'Asset with slug {asset_slug} not found')

    validator = URLValidator()
    try:

        if not asset.external and asset.asset_type == 'LESSON':
            slug = Path(asset.readme_url).stem
            url = 'https://content.breatheco.de/en/lesson/' + slug + '?plain=true'
            if ENV == 'development':
                return render_message(request, 'Redirect to: ' + url)
            else:
                return HttpResponseRedirect(redirect_to=url)

        validator(asset.url)
        if asset.gitpod:
            return HttpResponseRedirect(redirect_to='https://gitpod.io#' + asset.url)
        else:
            return HttpResponseRedirect(redirect_to=asset.url)
    except Exception as e:
        logger.error(e)
        msg = f'The url for the {asset.asset_type.lower()} your are trying to open ({asset_slug}) was not found, this error has been reported and will be fixed soon.'
        AssetErrorLog(slug=AssetErrorLog.INVALID_URL,
                      path=asset_slug,
                      asset=asset,
                      asset_type=asset.asset_type,
                      status_text=msg).save()
        return render_message(request, msg)


@api_view(['GET'])
@permission_classes([AllowAny])
def render_preview_html(request, asset_slug):
    asset = Asset.get_by_slug(asset_slug, request)
    if asset is None:
        return render_message(request, f'Asset with slug {asset_slug} not found')

    readme = asset.get_readme(parse=True)
    return render(request, 'markdown.html', {
        **AssetBigSerializer(asset).data, 'html': readme['html'],
        'frontmatter': readme['frontmatter'].items()
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def get_technologies(request):
    tech = AssetTechnology.objects.all()

    serializer = AssetTechnologySerializer(tech, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_translations(request):
    langs = Asset.objects.all().values_list('lang', flat=True)
    langs = set(langs)

    return Response([{'slug': l, 'title': l} for l in langs])


@api_view(['POST'])
@permission_classes([AllowAny])
def handle_test_syllabus(request):
    report = test_syllabus(request.data)
    return Response({'status': 'ok'})


@api_view(['POST'])
@permission_classes([AllowAny])
def handle_test_asset(request):
    report = test_asset(request.data)
    return Response({'status': 'ok'})


@api_view(['GET'])
@permission_classes([AllowAny])
@xframe_options_exempt
def render_readme(request, asset_slug, extension='raw'):
    asset = Asset.get_by_slug(asset_slug, request)
    if asset is None:
        raise ValidationException('Asset {asset_slug} not found', status.HTTP_404_NOT_FOUND)

    readme = asset.get_readme(parse=True)

    response = HttpResponse('Invalid extension format', content_type='text/html')
    if extension == 'html':
        response = HttpResponse(readme['html'], content_type='text/html')
        response['Content-Length'] = len(readme['html'])
    elif extension in ['md', 'mdx', 'txt']:
        response = HttpResponse(readme['decoded'], content_type='text/markdown')
        response['Content-Length'] = len(readme['decoded'])
    elif extension == 'ipynb':
        response = HttpResponse(readme['decoded'], content_type='application/json')
        response['Content-Length'] = len(readme['decoded'])

    # response[
    # 'Content-Security-Policy'] = "frame-ancestors 'self' https://4geeks.com http://localhost:3000 https://dev.4geeks.com"
    return response


@api_view(['GET'])
@permission_classes([AllowAny])
def get_config(request, asset_slug):
    asset = Asset.get_by_slug(asset_slug, request)
    if asset is None:
        raise ValidationException(f'Asset not {asset_slug} found', status.HTTP_404_NOT_FOUND)

    main_branch = 'master'
    response = requests.head(f'{asset.url}/tree/{main_branch}', allow_redirects=False)
    if response.status_code == 302:
        main_branch = 'main'

    try:
        response = requests.get(f'{asset.url}/blob/{main_branch}/learn.json?raw=true')
        if response.status_code == 404:
            response = requests.get(f'{asset.url}/blob/{main_branch}/bc.json?raw=true')
            if response.status_code == 404:
                raise ValidationException(f'Config file not found for {asset.url}',
                                          code=404,
                                          slug='config_not_found')

        return Response(response.json())
    except Exception as e:
        data = {
            'MESSAGE':
            f'learn.json or bc.json not found or invalid for for: \n {asset.url}',
            'TITLE':
            f'Error fetching the exercise meta-data learn.json for {asset.asset_type.lower()} {asset.slug}',
        }

        to = SYSTEM_EMAIL
        if asset.author is not None:
            to = asset.author.email

        send_email_message('message', to=to, data=data)
        raise ValidationException(f'Config file invalid or not found for {asset.url}',
                                  code=404,
                                  slug='config_not_found')


# Create your views here.
class AssetView(APIView):
    """
    List all snippets, or create a new snippet.
    """
    permission_classes = [AllowAny]

    def get(self, request, asset_slug=None):

        if asset_slug is not None:
            asset = Asset.get_by_slug(asset_slug, request)
            if asset is None:
                raise ValidationException(f'Asset {asset_slug} not found', status.HTTP_404_NOT_FOUND)

            serializer = AssetBigSerializer(asset)
            return Response(serializer.data)

        items = Asset.objects.all()
        lookup = {}

        if 'author' in self.request.GET:
            param = self.request.GET.get('author')
            lookup['author__id'] = param

        like = request.GET.get('like', None)
        if like is not None:
            items = items.filter(
                Q(slug__icontains=like) | Q(title__icontains=like)
                | Q(assetalias__slug__icontains=like))

        if 'type' in self.request.GET:
            param = self.request.GET.get('type')
            lookup['asset_type__iexact'] = param

        if 'slug' in self.request.GET:
            asset_type = self.request.GET.get('type', None)
            param = self.request.GET.get('slug')
            asset = Asset.get_by_slug(param, request, asset_type=asset_type)
            if asset is not None:
                lookup['slug'] = asset.slug
            else:
                lookup['slug'] = param

        if 'language' in self.request.GET:
            param = self.request.GET.get('language')
            if param == 'en':
                param = 'us'
            lookup['lang'] = param

        if 'visibility' in self.request.GET:
            param = self.request.GET.get('visibility')
            lookup['visibility__in'] = [p.upper() for p in param.split(',')]
        else:
            lookup['visibility'] = 'PUBLIC'

        if 'technologies' in self.request.GET:
            param = self.request.GET.get('technologies')
            lookup['technologies__in'] = [p.lower() for p in param.split(',')]

        if 'status' in self.request.GET:
            param = self.request.GET.get('status')
            lookup['status__in'] = [p.upper() for p in param.split(',')]

        if 'video' in self.request.GET:
            param = self.request.GET.get('video')
            if param == 'true':
                lookup['with_video'] = True

        if 'interactive' in self.request.GET:
            param = self.request.GET.get('interactive')
            if param == 'true':
                lookup['interactive'] = True

        if 'graded' in self.request.GET:
            param = self.request.GET.get('graded')
            if param == 'true':
                lookup['graded'] = True

        items = items.filter(**lookup).order_by('-created_at')

        if 'big' in self.request.GET:
            serializer = AssetMidSerializer(items, many=True)
        else:
            serializer = AssetSerializer(items, many=True)
        return Response(serializer.data)

    @capable_of('crud_asset')
    def post(self, request, academy_id=None):

        serializer = PostAssetSerializer(data=request.data,
                                         context={
                                             'request': request,
                                             'academy': academy_id
                                         })
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
