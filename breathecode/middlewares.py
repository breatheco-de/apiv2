import functools
import gzip
from io import BytesIO
import os
import sys
from django.utils.deprecation import MiddlewareMixin

IS_TEST = os.getenv('ENV', '') not in ['production', 'staging', 'development']
ENABLE_LIST_OPTIONS = ['true', '1', 'yes', 'y']


@functools.lru_cache(maxsize=1)
def is_compression_enabled():
    return os.getenv('COMPRESSION', '1').lower() in ENABLE_LIST_OPTIONS


@functools.lru_cache(maxsize=1)
def min_compression_size():
    return int(os.getenv('MIN_COMPRESSION_SIZE', '10'))


def must_compress(data):
    size = min_compression_size()
    if size == 0:
        return True

    return sys.getsizeof(data) / 1024 > size


class CompressResponseMiddleware(MiddlewareMixin):

    def process_response(self, request, response):
        # If the response is already compressed, do nothing
        if 'Content-Encoding' in response.headers or is_compression_enabled() is False or must_compress(
                response.content) is False or IS_TEST:
            return response

        # Compress the response if it's large enough
        if response.content:
            accept_encoding = request.META.get('HTTP_ACCEPT_ENCODING', '')
            if 'gzip' in accept_encoding:
                buffer = BytesIO()
                with gzip.GzipFile(fileobj=buffer, mode='wb') as f:
                    f.write(response.content)
                compressed_content = buffer.getvalue()

                response.content = compressed_content
                response['Content-Encoding'] = 'gzip'
                response['Content-Length'] = str(len(compressed_content))

        return response
