# from breathecode.media.schemas import MediaSchema
import base64
import json
import msgpack
from breathecode.authenticate.actions import get_user_language
from breathecode.authenticate.models import ProfileAcademy
from breathecode.media.schemas import FileSchema, MediaSchema
import os, hashlib, requests, logging, datetime
from breathecode.services.google_cloud import FunctionV1
from django.shortcuts import redirect
from breathecode.media.models import FileChunkUploadFailed, FileUpload, Media, Category, MediaResolution
from breathecode.services.google_cloud.function_v2 import FunctionV2
from breathecode.services.google_cloud.storage import Storage
from breathecode.utils import GenerateLookupsMixin, num_to_roman
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet
from breathecode.utils import ValidationException, capable_of
from rest_framework.response import Response
from rest_framework.parsers import FileUploadParser, MultiPartParser
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.http import StreamingHttpResponse
from django.db.models import Q, F
from breathecode.media.serializers import (GetMediaSerializer, MediaSerializer, MediaPUTSerializer,
                                           GetCategorySerializer, CategorySerializer, GetResolutionSerializer)
from slugify import slugify

from breathecode.utils.api_view_extensions.api_view_extensions import APIViewExtensions
from breathecode.utils.i18n import translation
from django.utils import timezone
from django.db.models import Sum

logger = logging.getLogger(__name__)
MIME_ALLOW = [
    'image/png', 'image/svg+xml', 'image/jpeg', 'image/gif', 'video/quicktime', 'video/mp4', 'audio/mpeg',
    'application/pdf', 'image/jpg'
]


def media_gallery_bucket():
    return os.getenv('MEDIA_GALLERY_BUCKET')


def google_project_id():
    return os.getenv('GOOGLE_PROJECT_ID', '')


def upload_bucket():
    return os.getenv('UPLOAD_BUCKET')


def get_transfer_file_url():
    return os.getenv('GCLOUD_TRANSFER_FILE', '')


class MediaView(ViewSet, GenerateLookupsMixin):
    """
    get:
        Return a list of Media.

    put:
        Update the categories of a Media in bulk.

    put_id:
        Update a Media by id.

    delete:
        Remove many Media with many ids passed through of id in the querystring.

    delete_id:
        Remove a Media by id.

    get_id:
        Media by id.

    get_slug:
        Media by slug.

    get_name:
        Media by name.
    """
    schema = MediaSchema()
    extensions = APIViewExtensions(sort='-created_at', paginate=True)

    @capable_of('read_media')
    def get(self, request, academy_id=None):
        handler = self.extensions(request)

        lookups = self.generate_lookups(request,
                                        many_fields=['mime', 'name', 'slug', 'id'],
                                        many_relationships=['academy'])

        items = Media.objects.filter(**lookups)

        # filter media by all categories, if one request have category 1 and 2,
        # if just get the media is in all the categories passed
        categories = request.GET.get('categories')
        if categories:
            categories = categories.split(',')
            for category in categories:
                items = items.filter(categories__pk=category)

        start = request.GET.get('start', None)
        if start is not None:
            start_date = datetime.datetime.strptime(start, '%Y-%m-%d').date()
            lookups['created_at__gte'] = start_date

        end = request.GET.get('end', None)
        if end is not None:
            end_date = datetime.datetime.strptime(end, '%Y-%m-%d').date()
            lookups['created_at__lte'] = end_date

        tp = request.GET.get('type')
        if tp:
            items = items.filter(mime__icontains=tp)

        items = items.filter(**lookups)

        like = request.GET.get('like')
        if like:
            items = items.filter(Q(name__icontains=like) | Q(slug__icontains=like))

        items = handler.queryset(items)
        serializer = GetMediaSerializer(items, many=True)

        return handler.response(serializer.data)

    @capable_of('read_media')
    def get_id(self, request, media_id: int, academy_id=None):
        item = Media.objects.filter(id=media_id).first()

        if not item:
            raise ValidationException('Media not found', code=404)

        serializer = GetMediaSerializer(item, many=False)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @capable_of('read_media')
    def get_slug(self, request, media_slug: str, academy_id=None):
        item = Media.objects.filter(slug=media_slug).first()

        if not item:
            raise ValidationException('Media not found', code=404)

        serializer = GetMediaSerializer(item, many=False)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @capable_of('read_media')
    def get_name(self, request, media_name: str, academy_id=None):
        item = Media.objects.filter(name=media_name).first()

        if not item:
            raise ValidationException('Media not found', code=404)

        serializer = GetMediaSerializer(item, many=False)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @capable_of('crud_media')
    def put(self, request, academy_id=None):
        many = isinstance(request.data, list)
        current = []
        context = {
            'request': request,
            'media_id': None,
            'many': True,
        }

        if not request.data:
            raise ValidationException('Please input data to use request', slug='no-args')

        for x in request.data:

            if not 'categories' in x:
                raise ValidationException('For bulk mode, please input category in the request',
                                          slug='categories-not-in-bulk')

            if len(x) > 2:
                raise ValidationException('Bulk mode its only to edit categories, ' +
                                          'please change to single put for more',
                                          slug='extra-args-bulk-mode')

            if not 'id' in x:
                raise ValidationException('Please input id in body for bulk mode', slug='id-not-in-bulk')

            media = Media.objects.filter(id=x['id']).first()
            if not media:
                raise ValidationException('Media not found', code=404, slug='media-not-found')

            if media.academy_id != int(academy_id):
                raise ValidationException("You can't edit media belonging to other academies",
                                          slug='different-academy-media-put')

            current.append(media)

        serializer = MediaSerializer(current, data=request.data, context=context, many=many)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of('crud_media')
    def put_id(self, request, media_id, academy_id=None):
        context = {
            'request': request,
            'media_id': media_id,
            'many': False,
        }

        current = Media.objects.filter(id=media_id).first()

        if not current:
            raise ValidationException('Media not found', code=404, slug='media-not-found')

        if current.academy_id != int(academy_id):
            raise ValidationException("You can't edit media belonging to other academies",
                                      slug='different-academy-media-put')

        serializer = MediaSerializer(current, data=request.data, context=context, many=False)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of('crud_media')
    def delete(self, request, academy_id=None):
        from ..services.google_cloud import Storage

        lookups = self.generate_lookups(request, many_fields=['id'])

        if lookups:
            items = Media.objects.filter(**lookups)

            if items.filter(academy__id=academy_id).count() != len(items):
                raise ValidationException('You may not delete media that belongs to a different academy',
                                          slug='academy-different-than-media-academy')

            for item in items:
                url = item.url
                hash = item.hash
                item.delete()

                if not Media.objects.filter(hash=hash).count():
                    storage = Storage()
                    file = storage.file(media_gallery_bucket(), url)
                    file.delete()

                    resolution = MediaResolution.objects.filter(hash=hash).first()
                    if resolution:
                        resolution_url = f'{url}-{resolution.width}x{resolution.height}'
                        resolution_file = storage.file(media_gallery_bucket(), resolution_url)
                        resolution_file.delete()

                        resolutions = MediaResolution.objects.filter(hash=hash)
                        for resolution in resolutions:
                            resolution.delete()

        return Response(None, status=status.HTTP_204_NO_CONTENT)

    @capable_of('crud_media')
    def delete_id(self, request, media_id=None, academy_id=None):
        from ..services.google_cloud import Storage

        data = Media.objects.filter(id=media_id).first()
        if not data:
            raise ValidationException('Media not found', code=404)

        if not data.academy or data.academy.id != int(academy_id):
            raise ValidationException('You may not delete media that belongs to a different academy',
                                      slug='academy-different-than-media-academy')

        url = data.url
        hash = data.hash
        data.delete()

        if not Media.objects.filter(hash=hash).count():
            storage = Storage()
            file = storage.file(media_gallery_bucket(), url)
            file.delete()

            resolution = MediaResolution.objects.filter(hash=hash).first()
            if resolution:
                resolution_url = f'{url}-{resolution.width}x{resolution.height}'
                resolution_file = storage.file(media_gallery_bucket(), resolution_url)
                resolution_file.delete()

                resolutions = MediaResolution.objects.filter(hash=hash)
                for resolution in resolutions:
                    resolution.delete()

        return Response(None, status=status.HTTP_204_NO_CONTENT)


class CategoryView(ViewSet):
    """
    get:
        Get a Category.

    get_id:
        Get a Category by id.

    get_slug:
        Get a Category by slug.

    post:
        Add a new Category.

    post:
        Add a new Category.

    put:
        Update a Category by slug.

    delete:
        Delete a Category by slug.
    """
    extensions = APIViewExtensions(paginate=True)

    @capable_of('read_media')
    def get(self, request, category_id=None, category_slug=None, academy_id=None):
        handler = self.extensions(request)

        items = Category.objects.filter()
        items = handler.queryset(items)
        serializer = GetCategorySerializer(items, many=True)

        return handler.response(serializer.data)

    @capable_of('read_media')
    def get_id(self, request, category_id=None, academy_id=None):
        item = Category.objects.filter(id=category_id).first()

        if not item:
            raise ValidationException('Category not found', code=404)

        serializer = GetCategorySerializer(item, many=False)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @capable_of('read_media')
    def get_slug(self, request, category_slug=None, academy_id=None):
        item = Category.objects.filter(slug=category_slug).first()

        if not item:
            raise ValidationException('Category not found', code=404)

        serializer = GetCategorySerializer(item, many=False)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @capable_of('crud_media')
    def post(self, request, academy_id=None):
        serializer = CategorySerializer(data=request.data, many=False)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of('crud_media')
    def put(self, request, category_slug=None, academy_id=None):
        data = Category.objects.filter(slug=category_slug).first()
        if not data:
            raise ValidationException('Category not found', code=404)

        serializer = CategorySerializer(data, data=request.data, many=False)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of('crud_media')
    def delete(self, request, category_slug=None, academy_id=None):
        data = Category.objects.filter(slug=category_slug).first()
        if not data:
            raise ValidationException('Category not found', code=404)

        if Media.objects.filter(categories__slug=category_slug).count():
            raise ValidationException('Category contain some medias', code=403)

        data.delete()

        return Response(None, status=status.HTTP_204_NO_CONTENT)


# DEPRECATED, use ChunkedUploadView instead
class UploadView(APIView):
    """
    put:
        Upload a file to Google Cloud.
    """
    parser_classes = [MultiPartParser, FileUploadParser]

    # permission_classes = [AllowAny]

    # upload was separated because in one moment I think that the serializer
    # not should get many create and update operations together
    def upload(self, request, academy_id=None, update=False):
        from ..services.google_cloud import Storage

        files = request.data.getlist('file')
        names = request.data.getlist('name')
        result = {
            'data': [],
            'instance': [],
        }

        file = request.data.get('file')
        slugs = []

        if not file:
            raise ValidationException('Missing file in request', code=400)

        if not len(files):
            raise ValidationException('empty files in request')

        if not len(names):
            for file in files:
                names.append(file.name)

        elif len(files) != len(names):
            raise ValidationException('numbers of files and names not match')

        # files validation below
        for index in range(0, len(files)):
            file = files[index]
            if file.content_type not in MIME_ALLOW:
                raise ValidationException(
                    f'You can upload only files on the following formats: {",".join(MIME_ALLOW)}')

        for index in range(0, len(files)):
            file = files[index]
            name = names[index] if len(names) else file.name
            file_bytes = file.read()
            hash = hashlib.sha256(file_bytes).hexdigest()
            slug = slugify(name)

            slug_number = Media.objects.filter(slug__startswith=slug).exclude(hash=hash).count() + 1
            if slug_number > 1:
                while True:
                    roman_number = num_to_roman(slug_number, lower=True)
                    slug = f'{slug}-{roman_number}'
                    if not slug in slugs:
                        break
                    slug_number = slug_number + 1

            slugs.append(slug)
            data = {
                'hash': hash,
                'slug': slug,
                'mime': file.content_type,
                'name': name,
                'categories': [],
                'academy': academy_id,
            }

            # it is receive in url encoded
            if 'categories' in request.data:
                data['categories'] = request.data['categories'].split(',')
            elif 'Categories' in request.headers:
                data['categories'] = request.headers['Categories'].split(',')

            media = Media.objects.filter(hash=hash, academy__id=academy_id).first()
            if media:
                data['id'] = media.id

                url = Media.objects.filter(hash=hash).values_list('url', flat=True).first()
                if url:
                    data['url'] = url

            else:
                url = Media.objects.filter(hash=hash).values_list('url', flat=True).first()
                if url:
                    data['url'] = url

                else:
                    # upload file section
                    storage = Storage()
                    cloud_file = storage.file(media_gallery_bucket(), hash)
                    cloud_file.upload(file, content_type=file.content_type)
                    data['url'] = cloud_file.url()
                    data['thumbnail'] = data['url'] + '-thumbnail'

            result['data'].append(data)

        query = None
        datas_with_id = [x for x in result['data'] if 'id' in x]
        for x in datas_with_id:
            if query:
                query = query | Q(id=x['id'])
            else:
                query = Q(id=x['id'])

        if query:
            result['instance'] = Media.objects.filter(query)

        return result

    @capable_of('crud_media')
    def put(self, request, academy_id=None):
        upload = self.upload(request, academy_id, update=True)
        serializer = MediaPUTSerializer(upload['instance'],
                                        data=upload['data'],
                                        context=upload['data'],
                                        many=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MaskingUrlView(APIView):
    """
    get:
        Get file from Google Cloud.
    """
    parser_classes = [FileUploadParser]
    permission_classes = [AllowAny]
    schema = FileSchema()

    def get(self, request, media_id=None, media_slug=None):
        lookups = {}
        if media_id:
            lookups['id'] = media_id
        elif media_slug:
            lookups['slug'] = media_slug.split('.')[0]  #ignore extension

        width = request.GET.get('width')
        height = request.GET.get('height')

        media = Media.objects.filter(**lookups).first()
        if not media:
            raise ValidationException('Resource not found', code=404)

        url = media.url

        if width and height:
            raise ValidationException(
                'You need to pass either width or height, not both, in order to avoid losing aspect ratio',
                code=400,
                slug='width-and-height-in-querystring')

        if (width or height) and not media.mime.startswith('image/'):
            raise ValidationException('cannot resize this resource', code=400, slug='cannot-resize-media')

        # register click
        media.hits = media.hits + 1
        media.save()

        resolution = MediaResolution.objects.filter(Q(width=width)
                                                    | Q(height=height), hash=media.hash).first()

        if (width or height) and not resolution:
            func = FunctionV1(region='us-central1', project_id=google_project_id(), name='resize-image')

            func_request = func.call({
                'width': width,
                'height': height,
                'filename': media.hash,
                'bucket': media_gallery_bucket(),
            })

            res = func_request.json()

            if not res['status_code'] == 200 or not res['message'] == 'Ok':
                if 'message' in res:
                    raise ValidationException(res['message'], code=500, slug='cloud-function-bad-input')

                raise ValidationException('Unhandled request from cloud functions',
                                          code=500,
                                          slug='unhandled-cloud-function')

            width = res['width']
            height = res['height']
            resolution = MediaResolution(width=width, height=height, hash=media.hash)
            resolution.save()

        if (width or height):
            width = resolution.width
            height = resolution.height

            url = f'{url}-{width}x{height}'
            resolution.hits = resolution.hits + 1
            resolution.save()

        if request.GET.get('mask') != 'true':
            return redirect(url, permanent=True)

        response = requests.get(url, stream=True)
        resource = StreamingHttpResponse(
            response.raw,
            status=response.status_code,
            reason=response.reason,
        )

        header_keys = [
            x for x in response.headers.keys() if x != 'Transfer-Encoding' and x != 'Content-Encoding'
            and x != 'Keep-Alive' and x != 'Connection'
        ]

        for header in header_keys:
            resource[header] = response.headers[header]

        return resource


class ResolutionView(ViewSet):
    """
    get_id:
        Get Resolution by id.

    get_media_id:
        Get Resolution by Media.id.

    delete:
        Delete a Resolution by id.
    """

    @capable_of('read_media_resolution')
    def get_id(self, request, resolution_id: int, academy_id=None):
        resolutions = MediaResolution.objects.filter(id=resolution_id).first()
        if not resolutions:
            raise ValidationException('Resolution was not found', code=404, slug='resolution-not-found')

        media = Media.objects.filter(hash=resolutions.hash).first()

        if not media:
            resolutions.delete()
            raise ValidationException('Resolution was deleted for not having parent element',
                                      slug='resolution-media-not-found',
                                      code=404)

        serializer = GetResolutionSerializer(resolutions)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @capable_of('read_media_resolution')
    def get_media_id(self, request, media_id: int, academy_id=None):
        media = Media.objects.filter(id=media_id).first()
        if not media:
            raise ValidationException('Media not found', code=404, slug='media-not-found')

        resolutions = MediaResolution.objects.filter(hash=media.hash)
        if not resolutions:
            raise ValidationException('Resolution was not found', code=404, slug='resolution-not-found')

        serializer = GetResolutionSerializer(resolutions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @capable_of('crud_media_resolution')
    def delete(self, request, resolution_id=None, academy_id=None):
        from ..services.google_cloud import Storage

        resolution = MediaResolution.objects.filter(id=resolution_id).first()
        if not resolution:
            raise ValidationException('Resolution was not found', code=404, slug='resolution-not-found')

        media = Media.objects.filter(hash=resolution.hash).first()
        if not media:
            resolution.delete()
            raise ValidationException('Resolution was deleted for not having parent element',
                                      slug='resolution-media-not-found',
                                      code=404)

        hash = resolution.hash
        url = media.url
        url = f'{url}-{resolution.width}x{resolution.height}'

        resolution.delete()

        if not MediaResolution.objects.filter(hash=hash).count():
            storage = Storage()
            file = storage.file(media_gallery_bucket(), url)
            file.delete()

        return Response(None, status=status.HTTP_204_NO_CONTENT)


class ChunkedUploadView(APIView):

    def get_hash(self):
        # 4,294,967,296 combinations
        data = os.urandom(4)
        return hashlib.md5(data).hexdigest()

    def get_user_limit(self):
        return 1024 * os.getenv('USER_UPLOAD_LIMIT', 1024 * 20)

    def get_user_quota(self):
        return 1024 * os.getenv('USER_UPLOAD_QUOTA', 1024 * 100)

    def create_file(self):
        request = self.request

        if not (size := request.data.get('size')) or isinstance(size, int) or size < 1:
            raise ValidationException(
                translation(self.lang,
                            en='size must be a positive integer',
                            es='size debe ser un entero positivo',
                            slug='bad-size'))

        capable = ProfileAcademy.objects.filter(user=request.user.id,
                                                role__capabilities__slug='crud_media').count()

        utc_now = timezone.now()
        utc_now = utc_now.replace(hour=0, minute=0, second=0, microsecond=0)

        quota = FileUpload.objects.filter(user=request.user.id,
                                          created_at__gte=utc_now).aggregate(Sum('size'))['size__sum']
        if not capable and quota and quota + size > self.get_user_quota():
            raise ValidationException(translation(self.lang,
                                                  en='You have reached your daily upload quota',
                                                  es='Has alcanzado tu cuota de carga diaria',
                                                  slug='quota-exceeded'),
                                      slug='quota-exceeded')

        FileUpload.objects.create(total_chunks=total_chunks, hash=h, size_limit=upload_limit)

        if not (total_chunks := request.data.get('total_chunks')) or not isinstance(total_chunks,
                                                                                    int) or total_chunks < 1:
            raise ValidationException(translation(self.lang,
                                                  en='total_chunks must be a positive integer',
                                                  es='total_chunks debe ser un entero positivo',
                                                  slug='bad-total-chunks'),
                                      silent=True,
                                      slug='bad-total-chunks')

        h = self.get_hash()
        while FileUpload.objects.filter(hash=h).count():
            h = self.get_hash()

        upload_limit = None

        if not capable:
            upload_limit = self.get_user_limit()

        file = FileUpload.objects.create(total_chunks=total_chunks, hash=h, size_limit=upload_limit)

        return Response({
            'id': file.id,
            'status': 'CREATED',
            'chunk_size': self.max_chunk_size,
        },
                        status=status.HTTP_201_CREATED)

    def upload_chunk(self):
        request = self.request

        if not (chunk := request.data.get('chunk')):
            raise ValidationException(translation(self.lang,
                                                  en='chunk is required',
                                                  es='chunk es requerido',
                                                  slug='chunk-required'),
                                      silent=True,
                                      slug='chunk-required')

        if chunk.size > self.max_chunk_size:
            raise ValidationException(translation(self.lang,
                                                  en='chunk size exceeded',
                                                  es='tamaño de chunk excedido',
                                                  slug='chunk-size-exceeded'),
                                      silent=True,
                                      slug='chunk-size-exceeded')

        if not (chunk_number := request.data.get('chunk_number')):
            raise ValidationException(translation(self.lang,
                                                  en='chunk_number is required',
                                                  es='chunk_number es requerido',
                                                  slug='chunk-number-required'),
                                      silent=True,
                                      slug='chunk-number-required')

        file_upload = FileUpload.objects.filter(id=self.file_id).first()
        if not file_upload:
            raise ValidationException(
                translation(self.lang, en='File not found', es='Archivo no encontrado',
                            slug='file-not-found'))

        chunk_filename = f'{file_upload.hash}.{chunk_number}'

        try:
            storage = Storage()
            cloud_file = storage.file(upload_bucket(), chunk_filename)
            cloud_file.upload(chunk, content_type=chunk.content_type)

            # it's for reattemps
            FileChunkUploadFailed.objects.filter(file=file_upload, chunk_number=chunk_number).delete()

        except Exception:
            FileChunkUploadFailed.objects.get_or_create(file=file_upload, chunk_number=chunk_number)
            return Response({
                'id': file_upload.id,
                'status': 'ERROR',
            }, status=status.HTTP_201_CREATED)

        file_upload.uploaded_chunks = F('uploaded_chunks') + 1
        file_upload.status = 'PENDING'
        file_upload.save()

        return Response({
            'id': file_upload.id,
            'status': 'PENDING',
        }, status=status.HTTP_201_CREATED)

    def put(self, request):
        self.lang = 'en'
        self.file_id = request.data.get('id')
        self.max_chunk_size = 1024 * int(os.getenv('CHUNK_SIZE', 100))

        if not self.file_id:
            return self.create_file()

        return self.upload_chunk()


class JoinChunksView(APIView):

    def put(self, request):
        file_id = request.data['file_id']
        try:
            uploaded_file = FileUpload.objects.get(id=file_id)
        except FileUpload.DoesNotExist:
            return Response({'detail': 'File not found'}, status=status.HTTP_404_NOT_FOUND)

        # Now, you can save additional metadata about the file if needed
        uploaded_file.save()

        return Response({'status': 'JOINING'}, status=status.HTTP_200_OK)


class MediaClaimView(APIView):

    @capable_of('crud_media')
    def put(self, request, academy_id=None):
        from ..services.google_cloud import Storage

        lang = get_user_language(request)

        file_id = request.data['file_id']
        file_upload = FileUpload.objects.filter(id=file_id).first()

        if not file_upload:
            return Response({'detail': 'File not found'}, status=status.HTTP_404_NOT_FOUND)

        storage = Storage()
        cloud_file = storage.file(f'{file_upload.hash}.meta', hash)
        file = cloud_file.download()
        file = json.loads(file)

        hash = file['hash']
        mime = file['mime']

        params = {
            'sourceBucket': upload_bucket(),
            'destinationBucket': media_gallery_bucket(),
        }

        func = FunctionV2(get_transfer_file_url())
        res = func.call({'filename': hash, 'bucket': get_transfer_file_url()}, params=params, timeout=28)
        data = msgpack.loads(res.content)

        ###

        # files validation below
        if mime not in MIME_ALLOW:
            raise ValidationException(
                f'You can upload only files on the following formats: {",".join(MIME_ALLOW)}')

        slug = slugify(file_upload.name)

        slug_number = Media.objects.filter(slug__startswith=slug).exclude(hash=hash).count() + 1
        if slug_number > 1:
            while True:
                roman_number = num_to_roman(slug_number, lower=True)
                slug = f'{slug}-{roman_number}'

                if not Media.objects.filter(slug=slug).exclude(hash=hash).exists():
                    break

                slug_number += 1

        new_media = Media()

        media = Media.objects.filter(hash=hash, academy__id=academy_id).first()
        if media:
            raise ValidationException('Media already exists', code=409, slug='media-already-exists')

        if media:

            url = Media.objects.filter(hash=hash).values_list('url', flat=True).first()
            if url:
                data['url'] = url

        else:
            url = Media.objects.filter(hash=hash).values_list('url', flat=True).first()
            if url:
                data['url'] = url

            else:
                # upload file section
                storage = Storage()
                cloud_file = storage.file(media_gallery_bucket(), hash)
                # cloud_file.upload(file, content_type=file.content_type)
                data['url'] = cloud_file.url()
                data['thumbnail'] = data['url'] + '-thumbnail'

        new_media.hash = hash
        new_media.slug = slug
        new_media.mime = mime
        new_media.name = name

        # fields = ('id', 'url', 'thumbnail', 'hash', 'hits', 'slug', 'mime', 'name', 'categories', 'academy')

        serializer = GetMediaSerializer(media, many=False)
        return Response(serializer.data, status=status.HTTP_200_OK)

        # return Response({'status': 'JOINING'}, status=status.HTTP_200_OK)
