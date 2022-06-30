import requests, logging, os
from pathlib import Path
from django.shortcuts import render
from django.utils import timezone
from django.db.models import Q, Count
from django.http import HttpResponse
from django.core.validators import URLValidator
from .models import Asset, AssetAlias, AssetTechnology, AssetErrorLog, KeywordCluster, AssetCategory, AssetKeyword, AssetComment
from .actions import test_syllabus, test_asset, pull_from_github, test_asset
from breathecode.utils.api_view_extensions.api_view_extensions import APIViewExtensions
from breathecode.notify.actions import send_email_message
from breathecode.authenticate.models import ProfileAcademy
from .caches import AssetCache, AssetCommentCache
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from .serializers import (AssetSerializer, AssetBigSerializer, AssetMidSerializer, AssetTechnologySerializer,
                          PostAssetSerializer, AssetCategorySerializer, AssetKeywordSerializer,
                          KeywordClusterSerializer, AcademyAssetSerializer, AssetPUTSerializer,
                          AcademyCommentSerializer, PostAssetCommentSerializer, PutAssetCommentSerializer)
from breathecode.utils import ValidationException, capable_of, GenerateLookupsMixin
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
@xframe_options_exempt
def render_preview_html(request, asset_slug):
    asset = Asset.get_by_slug(asset_slug, request)
    if asset is None:
        return render_message(request, f'Asset with slug {asset_slug} not found')

    if asset.asset_type == 'QUIZ':
        return render_message(request, f'Quiz cannot be previewed')

    readme = asset.get_readme(parse=True)
    return render(
        request, readme['frontmatter']['format'] + '.html', {
            **AssetBigSerializer(asset).data, 'html': readme['html'],
            'theme': request.GET.get('theme', 'light'),
            'plain': request.GET.get('plain', 'false'),
            'styles':
            readme['frontmatter']['inlining']['css'][0] if 'inlining' in readme['frontmatter'] else None,
            'frontmatter': readme['frontmatter'].items()
        })


@api_view(['GET'])
@permission_classes([AllowAny])
def get_technologies(request):
    tech = AssetTechnology.objects.filter(parent__isnull=True)

    serializer = AssetTechnologySerializer(tech, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def get_categories(request):
    items = AssetCategory.objects.all()
    serializer = AssetCategorySerializer(items, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def get_keywords(request):
    items = AssetKeyword.objects.all()
    serializer = AssetKeywordSerializer(items, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def get_clusters(request):
    items = KeywordCluster.objects.all()
    serializer = KeywordClusterSerializer(items, many=True)
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

    is_parse = True
    if asset.asset_type == 'QUIZ':
        is_parse = False
    readme = asset.get_readme(parse=is_parse)

    response = HttpResponse('Invalid extension format', content_type='text/html')
    if extension == 'html':
        response = HttpResponse(readme['html'], content_type='text/html')
    elif extension in ['md', 'mdx', 'txt']:
        response = HttpResponse(readme['decoded'], content_type='text/markdown')
    elif extension == 'ipynb':
        response = HttpResponse(readme['decoded'], content_type='application/json')

    return response


@api_view(['GET'])
@permission_classes([AllowAny])
def get_alias_redirects(request):
    aliases = AssetAlias.objects.all()
    redirects = {}
    for a in aliases:
        if a.slug != a.asset.slug:
            redirects[a.slug] = a.asset.slug

    return Response(redirects)


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
class AssetView(APIView, GenerateLookupsMixin):
    """
    List all snippets, or create a new snippet.
    """
    permission_classes = [AllowAny]
    extensions = APIViewExtensions(cache=AssetCache, sort='-created_at', paginate=True)

    def get(self, request, asset_slug=None):
        handler = self.extensions(request)
        cache = handler.cache.get()
        if cache is not None:
            return Response(cache, status=status.HTTP_200_OK)

        if asset_slug is not None:
            asset = Asset.get_by_slug(asset_slug, request)
            if asset is None:
                raise ValidationException(f'Asset {asset_slug} not found', status.HTTP_404_NOT_FOUND)

            serializer = AssetBigSerializer(asset)
            return handler.response(serializer.data)

        items = Asset.objects.all()
        lookup = {}

        if 'author' in self.request.GET:
            param = self.request.GET.get('author')
            lookup['author__id'] = param

        if 'owner' in self.request.GET:
            param = self.request.GET.get('owner')
            lookup['owner__id'] = param

        like = request.GET.get('like', None)
        if like is not None:
            items = items.filter(
                Q(slug__icontains=like) | Q(title__icontains=like)
                | Q(assetalias__slug__icontains=like))

        if 'type' in self.request.GET:
            param = self.request.GET.get('type')
            lookup['asset_type__iexact'] = param

        if 'category' in self.request.GET:
            param = self.request.GET.get('category')
            lookup['category__slug__iexact'] = param

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

        lookup['external'] = False
        if 'external' in self.request.GET:
            param = self.request.GET.get('external')
            if param == 'true':
                lookup['external'] = True
            elif param == 'both':
                lookup.pop('external', None)

        need_translation = self.request.GET.get('need_translation', False)
        if need_translation == 'true':
            items = items.annotate(num_translations=Count('all_translations')).filter(num_translations__lte=1) \

        items = items.filter(**lookup)
        items = handler.queryset(items)

        if 'big' in self.request.GET:
            serializer = AssetMidSerializer(items, many=True)
        else:
            serializer = AssetSerializer(items, many=True)

        return handler.response(serializer.data)


# Create your views here.
class AcademyAssetActionView(APIView):
    """
    List all snippets, or create a new snippet.
    """
    @capable_of('crud_asset')
    def put(self, request, asset_slug, action_slug, academy_id=None):

        if asset_slug is None:
            raise ValidationException('Missing asset_slug')

        asset = Asset.objects.filter(slug=asset_slug, academy__id=academy_id).first()
        if asset is None:
            raise ValidationException('This asset does not exist for this academy', 404)

        try:
            if action_slug == 'test':
                test_asset(asset)
            elif action_slug == 'sync':
                pull_from_github(asset.slug)
        except Exception as e:
            pass

        serializer = AssetBigSerializer(asset)
        return Response(serializer.data, status=status.HTTP_200_OK)


# Create your views here.
class AcademyAssetView(APIView, GenerateLookupsMixin):
    """
    List all snippets, or create a new snippet.
    """
    extensions = APIViewExtensions(cache=AssetCache, sort='-created_at', paginate=True)

    @capable_of('read_asset')
    def get(self, request, asset_slug=None, academy_id=None):

        member = ProfileAcademy.objects.filter(user=request.user, academy__id=academy_id).first()
        if member is None:
            raise ValidationException(f"You don't belong to this academy", status.HTTP_400_BAD_REQUEST)

        handler = self.extensions(request)
        cache = handler.cache.get()
        if cache is not None:
            return Response(cache, status=status.HTTP_200_OK)

        if asset_slug is not None:
            asset = Asset.get_by_slug(asset_slug, request)
            if asset is None or (asset.academy is not None and asset.academy.id != academy_id):
                raise ValidationException(f'Asset {asset_slug} not found for this academy',
                                          status.HTTP_404_NOT_FOUND)

            serializer = AssetBigSerializer(asset)
            return handler.response(serializer.data)

        items = Asset.objects.filter(Q(academy__id=academy_id) | Q(academy__isnull=True))

        lookup = {}

        if 'author' in self.request.GET:
            param = self.request.GET.get('author')
            lookup['author__id'] = param

        if member.role.slug == 'content_writer':
            items = items.filter(owner__id=request.user.id)
        elif 'owner' in self.request.GET:
            param = self.request.GET.get('owner')
            lookup['owner__id'] = param

        like = request.GET.get('like', None)
        if like is not None:
            items = items.filter(
                Q(slug__icontains=like) | Q(title__icontains=like)
                | Q(assetalias__slug__icontains=like))

        if 'type' in self.request.GET:
            param = self.request.GET.get('type')
            lookup['asset_type__iexact'] = param

        if 'category' in self.request.GET:
            param = self.request.GET.get('category')
            lookup['category__slug__iexact'] = param

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

        if 'sync_status' in self.request.GET:
            param = self.request.GET.get('sync_status')
            lookup['sync_status__in'] = [p.upper() for p in param.split(',')]

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

        lookup['external'] = False
        if 'external' in self.request.GET:
            param = self.request.GET.get('external')
            if param == 'true':
                lookup['external'] = True
            elif param == 'both':
                lookup.pop('external', None)

        published_before = request.GET.get('published_before', '')
        if published_before != '':
            items = items.filter(Q(published_at__lte=published_before) | Q(published_at__isnull=True))

        need_translation = self.request.GET.get('need_translation', False)
        if need_translation == 'true':
            items = items.annotate(num_translations=Count('all_translations')).filter(num_translations__lte=1) \

        items = items.filter(**lookup)
        items = handler.queryset(items)

        serializer = AcademyAssetSerializer(items, many=True)

        return handler.response(serializer.data)

    @capable_of('crud_asset')
    def put(self, request, asset_slug=None, academy_id=None):
        if asset_slug is None:
            raise ValidationException('Missing asset_slug')

        asset = Asset.objects.filter(slug=asset_slug, academy__id=academy_id).first()
        if asset is None:
            raise NotFound('This asset does not exist for this academy')

        serializer = AssetPUTSerializer(asset,
                                        data=request.data,
                                        context={
                                            'request': request,
                                            'academy_id': academy_id
                                        })
        if serializer.is_valid():
            serializer.save()
            serializer = AcademyAssetSerializer(asset, many=False)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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


# Create your views here.
class AcademyAssetCommentView(APIView, GenerateLookupsMixin):
    """
    List all snippets, or create a new snippet.
    """
    extensions = APIViewExtensions(cache=AssetCommentCache, sort='-created_at', paginate=True)

    @capable_of('read_asset')
    def get(self, request, academy_id=None):

        handler = self.extensions(request)
        cache = handler.cache.get()
        if cache is not None:
            return Response(cache, status=status.HTTP_200_OK)

        items = AssetComment.objects.filter(asset__academy__id=academy_id)
        lookup = {}

        if 'asset' in self.request.GET:
            param = self.request.GET.get('asset')
            lookup['asset__slug__in'] = [p.lower() for p in param.split(',')]

        if 'resolved' in self.request.GET:
            param = self.request.GET.get('resolved')
            if param == 'true':
                lookup['resolved'] = True

        items = items.filter(**lookup)
        items = handler.queryset(items)

        serializer = AcademyCommentSerializer(items, many=True)
        return handler.response(serializer.data)

    @capable_of('crud_asset')
    def post(self, request, academy_id=None):

        payload = {**request.data, 'author': request.user.id}

        serializer = PostAssetCommentSerializer(data=payload,
                                                context={
                                                    'request': request,
                                                    'academy': academy_id
                                                })
        if serializer.is_valid():
            serializer.save()
            serializer = AcademyCommentSerializer(serializer.instance)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of('crud_asset')
    def put(self, request, comment_id, academy_id=None):

        if comment_id is None:
            raise ValidationException('Missing comment_id')

        comment = AssetComment.objects.filter(id=comment_id, asset__academy__id=academy_id).first()
        if comment is None:
            raise ValidationException('This comment does not exist for this academy', 404)

        data = {**request.data}
        if 'status' in request.data and request.data['status'] == 'UNASSIGNED':
            data['author'] = None

        serializer = PutAssetCommentSerializer(comment,
                                               data=data,
                                               context={
                                                   'request': request,
                                                   'academy': academy_id
                                               })
        if serializer.is_valid():
            serializer.save()
            serializer = AcademyCommentSerializer(serializer.instance)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of('crud_asset')
    def delete(self, request, comment_id=None, academy_id=None):

        if comment_id is None:
            raise ValidationException('Missing comment ID on the URL', 404)

        comment = AssetComment.objects.filter(id=comment_id, asset__academy__id=academy_id).first()
        if comment is None:
            raise ValidationException('This comment does not exist', 404)

        comment.delete()
        return Response(None, status=status.HTTP_204_NO_CONTENT)
