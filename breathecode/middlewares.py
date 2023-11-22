import functools
import gzip
import os
import sys
import zlib
from django.utils.deprecation import MiddlewareMixin
import zstandard

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


@functools.lru_cache(maxsize=1)
def use_gzip():
    return os.getenv('USE_GZIP', '0').lower() in ENABLE_LIST_OPTIONS


class CompressResponseMiddleware(MiddlewareMixin):

    def _compress(self, response, encoding, alg):
        if self._has_content:
            compressed_content = alg(response.content)
            response.content = compressed_content

        else:
            compressed_content = alg(response.streaming_content)
            response.streaming_content = compressed_content

        response['Content-Encoding'] = encoding
        # response['Content-Length'] = str(len(compressed_content))

    def _must_compress(self, response):
        self._has_content = hasattr(response, 'content')

        if self._has_content:
            return must_compress(response.content)

        else:
            return must_compress(response.streaming_content)

    def process_response(self, request, response):
        # If the response is already compressed, do nothing
        if 'Content-Encoding' in response.headers or is_compression_enabled() is False or self._must_compress(
                response) is False or IS_TEST:
            return response

        # Compress the response if it's large enough
        if response.content:
            accept_encoding = request.META.get('HTTP_ACCEPT_ENCODING', '')

            dont_force_gzip = not use_gzip()

            # sort by compression ratio and speed
            if 'zstd' in accept_encoding and dont_force_gzip:
                self._compress(response, 'zstd', zstandard.compress)

            # default to deflate
            if ('deflate' in accept_encoding or '*' in accept_encoding) and dont_force_gzip:
                self._compress(response, 'deflate', zlib.compress)

            elif 'gzip' in accept_encoding:
                self._compress(response, 'gzip', gzip.compress)

        return response
