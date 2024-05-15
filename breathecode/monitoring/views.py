import logging
import os

import stripe
from circuitbreaker import CircuitBreakerError
from django.db.models import Q
from django.http import StreamingHttpResponse
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from breathecode.admissions.models import Academy
from breathecode.authenticate.actions import get_user_language
from breathecode.monitoring import signals
from breathecode.utils import GenerateLookupsMixin, capable_of
from breathecode.utils.api_view_extensions.api_view_extensions import APIViewExtensions
from breathecode.utils.i18n import translation
from capyc.rest_framework.exceptions import ValidationException

from .actions import add_github_webhook, add_stripe_webhook
from .models import CSVDownload, CSVUpload, RepositorySubscription, RepositoryWebhook
from .serializers import (
    CSVDownloadSmallSerializer,
    CSVUploadSmallSerializer,
    RepositorySubscriptionSerializer,
    RepoSubscriptionSmallSerializer,
)
from .signals import github_webhook
from .tasks import async_unsubscribe_repo

logger = logging.getLogger(__name__)


def get_stripe_webhook_secret():
    return os.getenv('STRIPE_WEBHOOK_SECRET', '')


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
    lang = get_user_language(request)

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

            try:
                storage = Storage()
                cloud_file = storage.file(os.getenv('DOWNLOADS_BUCKET', None), download.name)
                buffer = cloud_file.stream_download()

            except CircuitBreakerError:
                raise ValidationException(translation(
                    lang,
                    en='The circuit breaker is open due to an error, please try again later',
                    es='El circuit breaker está abierto debido a un error, por favor intente más tarde',
                    slug='circuit-breaker-open'),
                                          slug='circuit-breaker-open',
                                          data={'service': 'Google Cloud Storage'},
                                          silent=True,
                                          code=503)

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
def process_github_webhook(request, subscription_token):

    subscription = RepositorySubscription.objects.filter(token=subscription_token).first()
    if subscription is None:
        raise ValidationException(f'Subscription not found with token {subscription_token}')

    if subscription.status == 'DISABLED':
        logger.debug('Ignored because subscription has been disabled')
        async_unsubscribe_repo.delayed(subscription.hook_id, force_delete=False)
        return Response('Ignored because subscription has been disabled', status=status.HTTP_200_OK)

    academy_slugs = set([subscription.owner.slug] + [academy.slug for academy in subscription.shared_with.all()])
    payload = request.data.copy()
    payload['scope'] = request.headers['X-GitHub-Event']

    if 'repository' in payload and subscription.repository != payload['repository']['html_url']:
        raise ValidationException('Webhook was called from a different repository than its original subscription: ' +
                                  payload['repository']['html_url'])

    if payload['scope'] == 'ping':
        subscription.status = 'OPERATIONAL'
        subscription.status_message = 'Answered github ping successfully'
        subscription.save()
        return Response('Ready', status=status.HTTP_200_OK)

    for academy_slug in academy_slugs:
        webhook = add_github_webhook(payload, academy_slug)
        if webhook:
            logger.debug('triggering signal github_webhook: ' + payload['scope'])
            github_webhook.send(instance=webhook, sender=RepositoryWebhook)
            return Response(payload, status=status.HTTP_200_OK)
        else:
            logger.debug(f'Error at processing github webhook from academy {academy_slug}')
            raise ValidationException(f'Error at processing github webhook from academy {academy_slug}')


@api_view(['POST'])
@permission_classes([AllowAny])
def process_stripe_webhook(request):
    event = None
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature', None)
    endpoint_secret = get_stripe_webhook_secret()

    try:
        if not sig_header:
            raise stripe.error.SignatureVerificationError(None, None)

        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)

    except ValueError:
        raise ValidationException('Invalid payload', code=400, slug='invalid-payload')

    except stripe.error.SignatureVerificationError:
        raise ValidationException('Not allowed', code=403, slug='not-allowed')

    if event := add_stripe_webhook(event):
        signals.stripe_webhook.send(event=event, sender=event.__class__)

    return Response({'success': True})


class RepositorySubscriptionView(APIView, GenerateLookupsMixin):
    """
    List all snippets, or create a new snippet.
    """
    extensions = APIViewExtensions(sort='-created_at', paginate=True)

    @capable_of('read_asset')
    def get(self, request, academy_id=None):
        handler = self.extensions(request)

        _academy = Academy.objects.get(id=academy_id)
        items = RepositorySubscription.objects.filter(Q(shared_with=_academy) | Q(owner=_academy))
        lookup = {}

        if 'repository' in self.request.GET:
            param = self.request.GET.get('repository')
            items = items.filter(repository=param)

        items = items.filter(**lookup)
        items = handler.queryset(items)

        serializer = RepoSubscriptionSmallSerializer(items, many=True)

        return handler.response(serializer.data)

    @capable_of('crud_asset')
    def post(self, request, academy_id=None):
        lang = get_user_language(request)

        serializer = RepositorySubscriptionSerializer(data=request.data,
                                                      context={
                                                          'request': request,
                                                          'academy': academy_id,
                                                          'lang': lang
                                                      })
        if serializer.is_valid():
            instance = serializer.save()
            return Response(RepoSubscriptionSmallSerializer(instance).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of('crud_asset')
    def put(self, request, academy_id=None, subscription_id=None):
        lang = get_user_language(request)

        subs = RepositorySubscription.objects.filter(id=subscription_id).first()
        if subs is None:
            raise ValidationException(
                translation(lang,
                            en=f'No subscription has been found with id {subscription_id}',
                            es=f'No se ha encontrado una subscripcion con id {subscription_id}',
                            slug='subscription-not-found'))

        serializer = RepositorySubscriptionSerializer(subs,
                                                      data=request.data,
                                                      context={
                                                          'request': request,
                                                          'academy': academy_id,
                                                          'lang': lang
                                                      })
        if serializer.is_valid():
            instance = serializer.save()
            return Response(RepoSubscriptionSmallSerializer(instance).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
