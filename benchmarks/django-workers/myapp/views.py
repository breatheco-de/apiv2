import asyncio
import time
from typing import Optional

import aiohttp
import brotli
import httpx
import requests
from asgiref.sync import sync_to_async
from django.core.serializers import serialize
from django.http import HttpRequest, HttpResponse, HttpResponseNotFound, JsonResponse
from django.shortcuts import render

from .models import MyModel

aserialize = sync_to_async(serialize)

res = requests.get("https://jsonplaceholder.typicode.com/posts")
stored = res.content


async def async_range(count):
    for i in range(count):
        yield (i)


async def async_seed(request: HttpRequest, id: Optional[int] = None):
    async for i in async_range(30):
        await MyModel.objects.aget_or_create(name=f"name{i}", value=i)

    return JsonResponse({"status": "ok"})


def json_view(request: HttpRequest, id: Optional[int] = None):
    if id is not None:
        return JsonResponse({"name": "name", "value": 1})

    return JsonResponse([{"name": "name", "value": 1}], safe=False)


async def async_json_view(request: HttpRequest, id: Optional[int] = None):
    if id is not None:
        return JsonResponse({"name": "name", "value": 1})

    return JsonResponse([{"name": "name", "value": 1}], safe=False)


def json_query_view(request: HttpRequest, id: Optional[int] = None):
    if id is not None:
        res = MyModel.objects.aget(id=id)
        if res is None:
            raise HttpResponseNotFound("not found")

        return JsonResponse({"name": res.name, "value": res.value})

    keys = request.GET.keys()
    params = {k: request.GET[k] for k in keys}
    l = MyModel.objects.filter(**params)
    return JsonResponse([{"name": x.name, "value": x.value} for x in l], safe=False)


async def async_json_query_view(request: HttpRequest, id: Optional[int] = None):
    if id is not None:
        res = await MyModel.objects.aget(id=id)
        if res is None:
            raise HttpResponseNotFound("not found")

        return JsonResponse({"name": res.name, "value": res.value})

    keys = request.GET.keys()
    params = {k: request.GET[k] for k in keys}
    l = MyModel.objects.filter(**params)
    return JsonResponse([{"name": x.name, "value": x.value} async for x in l], safe=False)


def template_view(request: HttpRequest):
    l = MyModel.objects.filter()
    return render(request, "my_template.html", {"my_objects": l})


async def async_template_view(request: HttpRequest):
    l = MyModel.objects.filter()
    return render(request, "my_template.html", {"my_objects": [x async for x in l]})


def gateway_1s_view(request: HttpRequest):
    # eventbrite bug
    time.sleep(1)
    return JsonResponse({"status": "ok"})


async def async_gateway_1s_view(request: HttpRequest):
    # eventbrite bug
    await asyncio.sleep(1)
    return JsonResponse({"status": "ok"})


def gateway_3s_view(request: HttpRequest):
    # eventbrite bug
    time.sleep(3)
    return JsonResponse({"status": "ok"})


async def async_gateway_3s_view(request: HttpRequest):
    # eventbrite bug
    await asyncio.sleep(3)
    return JsonResponse({"status": "ok"})


def gateway_10s_view(request: HttpRequest):
    # eventbrite bug
    time.sleep(10)
    return JsonResponse({"status": "ok"})


async def async_gateway_10s_view(request: HttpRequest):
    # eventbrite bug
    await asyncio.sleep(10)
    return JsonResponse({"status": "ok"})


def requests_view(request: HttpRequest):
    # eventbrite bug
    try:
        response = requests.get("https://jsonplaceholder.typicode.com/posts", timeout=60)
        json = response.json()
    except Exception:
        return HttpResponse("timeout", status=408)
    return JsonResponse(json, safe=False)


async def async_requests_view(request: HttpRequest):
    # eventbrite bug
    try:
        response = requests.get("https://jsonplaceholder.typicode.com/posts", timeout=60)
        json = response.json()
    except Exception:
        return HttpResponse("timeout", status=408)
    return JsonResponse(json, safe=False)


def httpx_view(request: HttpRequest):
    # eventbrite bug
    try:
        response = httpx.get("https://jsonplaceholder.typicode.com/posts", timeout=60)
        json = response.json()
    except Exception:
        return HttpResponse("timeout", status=408)
    return JsonResponse(json, safe=False)


async def async_httpx_view(request: HttpRequest):
    # eventbrite bug
    async with httpx.AsyncClient(http2=True) as client:
        try:
            response = await client.get("https://jsonplaceholder.typicode.com/posts", timeout=60)
            json = response.json()
        except Exception:
            return HttpResponse("timeout", status=408)

    return JsonResponse(json, safe=False)


async def async_aiohttp_view(request: HttpRequest):
    # eventbrite bug
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get("https://jsonplaceholder.typicode.com/posts", timeout=60) as response:
                json = await response.json()
                return JsonResponse(json, safe=False)
        except Exception:
            return HttpResponse("timeout", status=408)


def brotli_view(request: HttpRequest):
    encoded = brotli.compress(stored)
    return HttpResponse(encoded)


async def async_brotli_view(request: HttpRequest):
    encoded = brotli.compress(stored)
    return HttpResponse(encoded)


def fake_cache_hit_view(request: HttpRequest):
    # latency issue
    time.sleep(0.02)
    return JsonResponse({"status": "ok"})


async def async_fake_cache_hit_view(request: HttpRequest):
    # latency issue
    await asyncio.sleep(0.02)
    return JsonResponse({"status": "ok"})


def fake_cache_set_view(request: HttpRequest):
    # with brotli
    time.sleep(0.2)
    return JsonResponse({"status": "ok"})


async def async_fake_cache_set_view(request: HttpRequest):
    # with brotli
    await asyncio.sleep(0.2)
    return JsonResponse({"status": "ok"})
