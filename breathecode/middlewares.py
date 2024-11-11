import functools
import gzip
import os
import sys
import zlib

import brotli
import zstandard
from asgiref.sync import iscoroutinefunction, sync_to_async
from django.http import HttpRequest, HttpResponseRedirect
from django.utils.decorators import sync_and_async_middleware
from django.utils.deprecation import MiddlewareMixin

ENV = os.getenv("ENV", "")
IS_TEST = ENV not in ["production", "staging", "development"]
IS_DEV = ENV != "production"
ENABLE_LIST_OPTIONS = ["true", "1", "yes", "y"]


@functools.lru_cache(maxsize=1)
def is_compression_enabled():
    return os.getenv("COMPRESSION", "1").lower() in ENABLE_LIST_OPTIONS


@functools.lru_cache(maxsize=1)
def min_compression_size():
    return int(os.getenv("MIN_COMPRESSION_SIZE", "10"))


def must_compress(data):
    size = min_compression_size()
    if size == 0:
        return True

    return sys.getsizeof(data) / 1024 > size


@functools.lru_cache(maxsize=1)
def use_gzip():
    return os.getenv("USE_GZIP", "0").lower() in ENABLE_LIST_OPTIONS


class CompressResponseMiddleware(MiddlewareMixin):

    def _compress(self, response, encoding, alg):
        if self._has_content:
            compressed_content = alg(response.content)
            response.content = compressed_content

        else:
            compressed_content = alg(response.streaming_content)
            response.streaming_content = compressed_content

        response["Content-Encoding"] = encoding
        # response['Content-Length'] = str(len(compressed_content))

    def _must_compress(self, response):
        self._has_content = hasattr(response, "content")

        if self._has_content:
            return must_compress(response.content)

        else:
            return must_compress(response.streaming_content)

    def process_response(self, request, response):
        # If the response is already compressed, do nothing
        if (
            "Content-Encoding" in response.headers
            or is_compression_enabled() is False
            or self._must_compress(response) is False
            or IS_TEST
        ):
            return response

        # Compress the response if it's large enough
        if response.content:
            accept_encoding = request.META.get("HTTP_ACCEPT_ENCODING", "")

            dont_force_gzip = not use_gzip()

            # sort by compression ratio and speed
            if "zstd" in accept_encoding and dont_force_gzip:
                self._compress(response, "zstd", zstandard.compress)

            elif ("deflate" in accept_encoding or "*" in accept_encoding) and dont_force_gzip:
                self._compress(response, "deflate", zlib.compress)

            elif "gzip" in accept_encoding:
                self._compress(response, "gzip", gzip.compress)

            elif IS_DEV and "br" in accept_encoding and "PostmanRuntime" in request.META.get("HTTP_USER_AGENT", ""):
                self._compress(response, "br", brotli.compress)

        return response


@sync_and_async_middleware
def static_redirect_middleware(get_response):
    path = "/static"

    def redirect(request):
        bucket = os.getenv("STATIC_BUCKET")
        gcs_base_url = f"https://storage.googleapis.com/{bucket}"
        full_url = f"{gcs_base_url}{request.path.replace(path, '')}"

        return HttpResponseRedirect(full_url)

    if iscoroutinefunction(get_response):

        async def middleware(request):
            if request.path.startswith(f"{path}/"):
                return redirect(request)

            response = await get_response(request)
            return response

    else:

        def middleware(request):
            if request.path.startswith(f"{path}/"):
                return redirect(request)

            response = get_response(request)
            return response

    return middleware


@sync_and_async_middleware
def set_service_header_middleware(get_response):
    def set_header(response):
        if "Service" not in response.headers:
            response.headers["Service"] = "BreatheCode"

    if iscoroutinefunction(get_response):

        async def middleware(request):
            response = await get_response(request)
            set_header(response)
            return response

    else:

        def middleware(request):
            response = get_response(request)
            set_header(response)
            return response

    return middleware


NO_PAGINATED = set()


@sync_and_async_middleware
def detect_pagination_issues_middleware(get_response):
    from breathecode.monitoring.models import NoPagination

    def instrument_no_pagination(request: HttpRequest) -> None:
        if request.method not in ["GET"]:
            return

        path = request.path
        method = request.method

        if (path, method) in NO_PAGINATED:
            return

        is_paginated = request.GET.get("limit") and request.GET.get("offset")

        if is_paginated is False and NoPagination.objects.filter(path=path, method=method).exists() is False:
            NO_PAGINATED.add((path, method))
            NoPagination.objects.create(path=path, method=method)

    @sync_to_async
    def ainstrument_no_pagination(request: HttpRequest) -> None:
        instrument_no_pagination(request)

    if iscoroutinefunction(get_response):

        async def middleware(request: HttpRequest):
            await ainstrument_no_pagination(request)

            response = await get_response(request)
            return response

    else:

        def middleware(request: HttpRequest):
            instrument_no_pagination(request)

            response = get_response(request)
            return response

    return middleware
