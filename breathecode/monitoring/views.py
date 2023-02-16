import os, requests, logging
from io import BytesIO, StringIO
from django.shortcuts import render
from django.utils import timezone
from .signals import github_webhook
from .models import Application, Endpoint, CSVDownload, CSVUpload, RepositorySubscription, RepositoryWebhook
from rest_framework.permissions import AllowAny
from .serializers import CSVDownloadSmallSerializer, CSVUploadSmallSerializer
from django.http import HttpResponseRedirect, HttpResponse
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from breathecode.utils import ValidationException
from rest_framework import status
from django.http import StreamingHttpResponse
from .actions import add_github_webhook

logger = logging.getLogger(__name__)


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


@api_view(['GET'])
@permission_classes([AllowAny])
def get_upload(request, upload_id=None):

    # if request.user.is_staff == False:
    #     raise ValidationException("You are not authorized to review this download",
    #                               code=status.HTTP_401_UNAUTHORIZED)

    if upload_id is not None:
        upload = CSVUpload.objects.filter(id=upload_id).first()
        if upload is None:
            raise ValidationException(f'CSV Upload {upload_id} not found', code=status.HTTP_404_NOT_FOUND)

        serializer = CSVUploadSmallSerializer(upload, many=False)
        return Response(serializer.data, status=status.HTTP_200_OK)

    csv = CSVUpload.objects.all()
    serializer = CSVUploadSmallSerializer(csv, many=True)

    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
# @renderer_classes([PlainTextRenderer])
def process_github_webhook(request, subscription_token):

    subscription = RepositorySubscription.objects.filter(token=subscription_token).first()
    if subscription is None:
        raise ValidationException(f'Subscription not found with token {subscription_token}')

    academy_slugs = set([subscription.owner.slug] +
                        [academy.slug for academy in subscription.shared_with.all()])
    payload = request.data
    payload['scope'] = request.headers['X-GitHub-Event']

    if subscription.repository != payload['repository']['html_url']:
        raise ValidationException(
            'Webhook was called from a different repository than its original subscription: ' +
            payload['repository']['html_url'])

    for academy_slug in academy_slugs:
        webhook = add_github_webhook(payload, academy_slug)
        if webhook:
            logger.debug('triggering signal github_webhook: ' + payload['scope'])
            github_webhook.send(instance=webhook, sender=RepositoryWebhook)
            return Response(payload, status=status.HTTP_200_OK)
        else:
            logger.debug(f'Error at processing github webhook from academy {academy_slug}')
            raise ValidationException(f'Error at processing github webhook from academy {academy_slug}')
