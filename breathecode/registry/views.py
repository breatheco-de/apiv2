import requests, logging
from django.shortcuts import render
from django.utils import timezone
from django.db.models import Q
from django.http import HttpResponse
from .models import Asset, AssetAlias, AssetTechnology
from breathecode.notify.actions import send_email_message
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from .serializers import (AssetSerializer, AssetBigSerializer, AssetMidSerializer, AssetTechnologySerializer,
                          PostAssetSerializer)
from breathecode.utils import ValidationException, capable_of
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.views import APIView
from rest_framework import status
from django.http import HttpResponseRedirect

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([AllowAny])
def redirect_gitpod(request, asset_slug):
    alias = AssetAlias.objects.filter(Q(slug=asset_slug) | Q(asset__slug=asset_slug)).first()
    if alias is None:
        raise ValidationException('Asset alias not found', status.HTTP_404_NOT_FOUND)

    if alias.asset.gitpod:
        return HttpResponseRedirect(redirect_to='https://gitpod.io#' + alias.asset.url)
    else:
        return HttpResponseRedirect(redirect_to=alias.asset.url)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_technologies(request):
    tech = AssetTechnology.objects.all()

    serializer = AssetTechnologySerializer(tech, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_readme(request, asset_slug):
    alias = AssetAlias.objects.filter(Q(slug=asset_slug) | Q(asset__slug=asset_slug)).first()
    if alias is None:
        raise ValidationException('Asset not found', status.HTTP_404_NOT_FOUND)

    return Response(alias.asset.readme)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_config(request, asset_slug):
    alias = AssetAlias.objects.filter(Q(slug=asset_slug) | Q(asset__slug=asset_slug)).first()
    if alias is None:
        raise ValidationException('Asset not found', status.HTTP_404_NOT_FOUND)

    asset = alias.asset
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
            'MESSAGE': f'learn.json or bc.json not found or invalid for for {asset.url}',
            'TITLE': f'Error fetching the exercise meta-data learn.json for {asset.slug}',
        }

        to = 'support@4geeksacademy.com'
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
            alias = AssetAlias.objects.filter(Q(slug=asset_slug) | Q(asset__slug=asset_slug)).first()
            if alias is None:
                raise ValidationException('Asset not found', status.HTTP_404_NOT_FOUND)

            serializer = AssetBigSerializer(alias.asset)
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
            param = self.request.GET.get('slug')
            lookup['slug'] = param

        if 'language' in self.request.GET:
            param = self.request.GET.get('language')
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
