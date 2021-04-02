import hashlib, requests
from django.shortcuts import redirect
from breathecode.media.serializers import (
    GetMediaSerializer,
    MediaSerializer,
    GetCategorySerializer,
    CategorySerializer
)
from breathecode.media.models import Media, Category
from breathecode.utils import GenerateLookupsMixin
from rest_framework.views import APIView
from breathecode.utils import ValidationException, capable_of, HeaderLimitOffsetPagination
from rest_framework.response import Response
from rest_framework.parsers import FileUploadParser
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.http import StreamingHttpResponse
from ..services.google_cloud import Storage


BUCKET_NAME = "media-breathecode"


class MediaView(APIView, HeaderLimitOffsetPagination, GenerateLookupsMixin):
    # permission_classes = [AllowAny]

    @capable_of('read_media')
    def get(self, request, media_id=None, media_slug=None, media_name=None, academy_id=None):
        if media_id:
            item = Media.objects.filter(id=media_id).first()

            if not item:
                raise ValidationException('Media not found', code=404)

            serializer = GetMediaSerializer(item, many=False)
            return Response(serializer.data, status=status.HTTP_200_OK)

        if media_slug:
            item = Media.objects.filter(slug=media_slug).first()

            if not item:
                raise ValidationException('Media not found', code=404)

            serializer = GetMediaSerializer(item, many=False)
            return Response(serializer.data, status=status.HTTP_200_OK)

        if media_name:
            item = Media.objects.filter(name=media_name).first()

            if not item:
                raise ValidationException('Media not found', code=404)

            serializer = GetMediaSerializer(item, many=False)
            return Response(serializer.data, status=status.HTTP_200_OK)


        lookups = self.generate_lookups(
            request,
            relationships=['academy']
        )

        items = Media.objects.filter(**lookups)

        page = self.paginate_queryset(items, request)
        serializer = GetMediaSerializer(page, many=True)

        if self.is_paginate(request):
            return self.get_paginated_response(serializer.data)
        else:
            return Response(serializer.data, status=status.HTTP_200_OK)

    @capable_of('crud_media')
    def put(self, request, media_id=None, academy_id=None):
        data = Media.objects.filter(id=media_id).first()
        if not data:
            raise ValidationException('Media not found', code=404)

        serializer = MediaSerializer(data, data=request.data, many=False)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of('crud_media')
    def delete(self, request, media_id=None, academy_id=None):
        data = Media.objects.filter(id=media_id).first()
        if not data:
            raise ValidationException('Media not found', code=404)

        url = data.url
        hash = data.hash
        data.delete()

        if not Media.objects.filter(hash=hash).count():
            storage = Storage()
            file = storage.file(BUCKET_NAME, url)
            file.delete()

        return Response(None, status=status.HTTP_204_NO_CONTENT)


class CategoryView(APIView, HeaderLimitOffsetPagination):
    # permission_classes = [AllowAny]

    @capable_of('read_media')
    def get(self, request, category_id=None, category_slug=None, academy_id=None):
        if category_id:
            item = Category.objects.filter(id=category_id).first()

            if not item:
                raise ValidationException('Category not found', code=404)

            serializer = GetCategorySerializer(item, many=False)
            return Response(serializer.data, status=status.HTTP_200_OK)

        if category_slug:
            item = Category.objects.filter(slug=category_slug).first()

            if not item:
                raise ValidationException('Category not found', code=404)

            serializer = GetCategorySerializer(item, many=False)
            return Response(serializer.data, status=status.HTTP_200_OK)

        items = Category.objects.filter()

        page = self.paginate_queryset(items, request)
        serializer = GetCategorySerializer(page, many=True)

        if self.is_paginate(request):
            return self.get_paginated_response(serializer.data)
        else:
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


class UploadView(APIView):
    parser_classes = [FileUploadParser]
    # permission_classes = [AllowAny]

    @capable_of('crud_media')
    def put(self, request, academy_id=None):
        file = request.data.get('file')
        if not file:
            raise ValidationException('Missing file in request', code=400)

        slug = file.name.split('.')[0]

        # we save one file just once
        hash = hashlib.sha256(file.read()).hexdigest()
        file = request.data.get('file')

        if Media.objects.filter(slug=slug).exclude(hash=hash).count():
            raise ValidationException('slug already exists', code=400)

        data = {
            'hash': hash,
            'slug': slug,
            'mime': file.content_type,
            'name': file.name,
            # 'url': 'https://www.youtube.com/watch?v=hCXNwpq2qVQ&list=PLRHmAOq1DquFWreKY5n9mWcrX6SvLvI6v&index=3',
            'categories': [],
            'academy_id': academy_id,
        }

        media = Media.objects.filter(hash=hash, academy__id=academy_id).first()
        if not media:
            url = Media.objects.filter(hash=hash).values_list('url', flat=True).first()
            if url:
                data['url'] = url

            else:
                # upload file section
                storage = Storage()
                cloud_file = storage.file(BUCKET_NAME, hash)
                cloud_file.upload(file.read(), public=True)
                data['url'] = cloud_file.url()

        if media:
            serializer = MediaSerializer(media, data=data, many=False)
        else:
            serializer = MediaSerializer(data=data, many=False)

        if serializer.is_valid():
            serializer.save()
            # add code
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MaskingUrlView(APIView):
    parser_classes = [FileUploadParser]
    permission_classes = [AllowAny]

    def get(self, request, media_id=None, media_slug=None):
        lookups = {}
        if media_id:
            lookups['id'] = media_id
        elif media_slug:
            lookups['slug'] = media_slug

        (url, hits) = Media.objects.filter(**lookups).values_list('url', 'hits').first()
        if not url:
            raise ValidationException('Resource not found', code=404)

        # register click
        Media.objects.filter(slug=media_slug).update(hits=hits + 1)
        if request.GET.get('mask') != 'true':
            return redirect(url, permanent=True)

        response = requests.get(url, stream=True)
        resource = StreamingHttpResponse(
            response.raw,
            status=response.status_code,
            reason=response.reason,
        )

        header_keys = [x for x in response.headers.keys() if x !=
            'Transfer-Encoding' and x != 'Content-Encoding' and x !=
            'Keep-Alive' and x != 'Connection']

        for header in header_keys:
            resource[header] = response.headers[header]

        return resource
