import requests
from django.shortcuts import render
from django.utils import timezone
from django.http import HttpResponse
from .models import Asset, AssetAlias, AssetTechnology
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from .serializers import (AssetSerializer, AssetBigSerializer,
                          AssetMidSerializer, AssetTechnologySerializer)
from breathecode.utils import ValidationException
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.views import APIView
from rest_framework import status
from django.http import HttpResponseRedirect


@api_view(['GET'])
@permission_classes([AllowAny])
def redirect_gitpod(request, asset_slug):
    alias = AssetAlias.objects.filter(slug=asset_slug).first()
    if alias is None:
        raise ValidationException("Asset alias not found",
                                  status.HTTP_404_NOT_FOUND)

    if alias.asset.gitpod:
        return HttpResponseRedirect(redirect_to='https://gitpod.io#' +
                                    alias.asset.url)
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
    asset = Asset.objects.filter(slug=asset_slug).first()
    if asset is None:
        raise ValidationException("Asset alias not found",
                                  status.HTTP_404_NOT_FOUND)

    return Response(asset.readme)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_config(request, asset_slug):
    asset = Asset.objects.filter(slug=asset_slug).first()
    if asset is None:
        raise ValidationException("Asset alias not found",
                                  status.HTTP_404_NOT_FOUND)

    response = requests.get(asset.url + "/blob/master/learn.json?raw=true")
    if response.status_code == 404:
        response = requests.get(asset.url + "/blob/master/bc.json?raw=true")
        if response.status_code == 404:
            raise ValidationException("Config file not found",
                                      code=404,
                                      slug='config_not_found')

    return Response(response.json())


# Create your views here.
class GetAssetView(APIView):
    """
    List all snippets, or create a new snippet.
    """
    permission_classes = [AllowAny]

    def get(self, request, asset_slug=None):

        if asset_slug is not None:
            asset = Asset.objects.filter(slug=asset_slug).first()
            if asset is None:
                raise ValidationException("Asset not found",
                                          status.HTTP_404_NOT_FOUND)

            serializer = AssetBigSerializer(asset)
            return Response(serializer.data)

        items = Asset.objects.all()
        lookup = {}

        if 'author' in self.request.GET:
            param = self.request.GET.get('author')
            lookup['author__id'] = param

        if 'type' in self.request.GET:
            param = self.request.GET.get('type')
            lookup['asset_type__iexact'] = param

        if 'slug' in self.request.GET:
            param = self.request.GET.get('academy')
            lookup['academy__id'] = param

        if 'language' in self.request.GET:
            param = self.request.GET.get('language')
            lookup['lang'] = param

        if 'visibility' in self.request.GET:
            param = self.request.GET.get('visibility')
            lookup['visibility__in'] = [p.upper() for p in param.split(",")]
        else:
            lookup['visibility'] = "PUBLIC"

        if 'technologies' in self.request.GET:
            param = self.request.GET.get('technologies')
            lookup['technologies__in'] = [p.lower() for p in param.split(",")]

        if 'status' in self.request.GET:
            param = self.request.GET.get('status')
            lookup['status__in'] = [p.upper() for p in param.split(",")]

        if 'video' in self.request.GET:
            param = self.request.GET.get('video')
            if param == "true":
                lookup['with_video'] = True

        if 'interactive' in self.request.GET:
            param = self.request.GET.get('interactive')
            if param == "true":
                lookup['interactive'] = True

        if 'graded' in self.request.GET:
            param = self.request.GET.get('graded')
            if param == "true":
                lookup['graded'] = True

        items = items.filter(**lookup).order_by('-created_at')

        if 'big' in self.request.GET:
            serializer = AssetMidSerializer(items, many=True)
        else:
            serializer = AssetSerializer(items, many=True)
        return Response(serializer.data)
