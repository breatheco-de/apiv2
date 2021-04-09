from django.shortcuts import render
from django.utils import timezone
from django.http import HttpResponse
from .models import Asset
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from .serializers import AssetSerializer, AssetBigSerializer
from breathecode.utils import APIException
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.views import APIView
from rest_framework import status
from django.http import HttpResponseRedirect

@api_view(['GET'])
@permission_classes([AllowAny])
def redirect_gitpod(request, asset_slug):
    asset = Asset.objects.filter(slug=asset_slug).first()
    if asset is None:
        raise exceptions.NotFound(detail="Asset not found", code=status.HTTP_404_NOT_FOUND)

    return HttpResponseRedirect(redirect_to='https://gitpod.io#'+package.url)

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
                raise APIException("Asset not found", code=status.HTTP_404_NOT_FOUND)

            serializer = AssetBigSerializer(asset)
            return Response(serializer.data)

        items = Asset.objects.all()
        lookup = {}

        if 'author' in self.request.GET:
            param = self.request.GET.get('author')
            lookup['author__id'] = param

        if 'type' in self.request.GET:
            param = self.request.GET.get('type')
            lookup['asset_type'] = param

        if 'slug' in self.request.GET:
            param = self.request.GET.get('academy')
            lookup['academy__id'] = param

        if 'language' in self.request.GET:
            param = self.request.GET.get('language')
            lookup['lang'] = param

        items = items.filter(**lookup).order_by('-created_at')
        
        serializer = AssetSerializer(items, many=True)
        return Response(serializer.data)