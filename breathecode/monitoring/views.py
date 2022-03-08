import os, requests
from io import BytesIO, StringIO
from django.shortcuts import render
from django.utils import timezone
from .models import Application, Endpoint, CSVDownload
from rest_framework.permissions import AllowAny
from .serializers import CSVDownloadSmallSerializer
from django.http import HttpResponseRedirect, HttpResponse
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from breathecode.utils import ValidationException
from rest_framework import status
from django.http import StreamingHttpResponse


@api_view(['GET'])
@permission_classes([AllowAny])
def get_endpoints(request):
    return Response([], status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_apps(request):
    return Response([], status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_download(request, download_id=None):

    # if request.user.is_staff == False:
    #     raise ValidationException("You are not authorized to review this download",
    #                               code=status.HTTP_401_UNAUTHORIZED)

    if download_id is not None:
        download = CSVDownload.objects.filter(id=download_id).first()
        if download is None:
            raise ValidationException(f'CSV Download {download_id} not found', code=status.HTTP_404_NOT_FOUND)

        raw = request.GET.get('raw', '')
        if raw == 'true':
            from ..services.google_cloud import Storage
            storage = Storage()
            cloud_file = storage.file(os.getenv('DOWNLOADS_BUCKET', None), download.name)
            buffer = cloud_file.stream_download()
            return StreamingHttpResponse(
                buffer.all(),
                content_type='text/csv',
                headers={'Content-Disposition': f'attachment; filename={download.name}'},
            )
        else:
            serializer = CSVDownloadSmallSerializer(download, many=False)
            return Response(serializer.data, status=status.HTTP_200_OK)

    csv = CSVDownload.objects.all()
    serializer = CSVDownloadSmallSerializer(csv, many=True)

    return Response(serializer.data, status=status.HTTP_200_OK)
