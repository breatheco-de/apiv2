"""
URL configuration for mysite project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

import myapp.views
from django.contrib import admin
from django.urls import path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("myapp/sync/json", myapp.views.json_view),
    path("myapp/sync/json/<int:id>", myapp.views.json_view),
    path("myapp/sync/json_query", myapp.views.json_query_view),
    path("myapp/sync/json_query/<int:id>", myapp.views.json_query_view),
    path("myapp/sync/template_query", myapp.views.template_view),
    path("myapp/sync/gateway_1s", myapp.views.gateway_1s_view),
    path("myapp/sync/gateway_3s", myapp.views.gateway_3s_view),
    path("myapp/sync/gateway_10s", myapp.views.gateway_10s_view),
    path("myapp/sync/requests", myapp.views.requests_view),
    path("myapp/sync/httpx", myapp.views.httpx_view),
    path("myapp/sync/brotli", myapp.views.brotli_view),
    path("myapp/sync/cache_hit", myapp.views.fake_cache_hit_view),
    path("myapp/sync/cache_set", myapp.views.fake_cache_set_view),
    path("myapp/async/seed", myapp.views.async_seed),
    path("myapp/async/json", myapp.views.async_json_view),
    path("myapp/async/json/<int:id>", myapp.views.async_json_view),
    path("myapp/async/json_query", myapp.views.async_json_query_view),
    path("myapp/async/json_query/<int:id>", myapp.views.async_json_query_view),
    path("myapp/async/template_query", myapp.views.async_template_view),
    path("myapp/async/gateway_1s", myapp.views.async_gateway_1s_view),
    path("myapp/async/gateway_3s", myapp.views.async_gateway_1s_view),
    path("myapp/async/gateway_10s", myapp.views.async_gateway_10s_view),
    path("myapp/async/requests", myapp.views.async_requests_view),
    path("myapp/async/httpx", myapp.views.async_httpx_view),
    path("myapp/async/aiohttp", myapp.views.async_aiohttp_view),
    path("myapp/async/brotli", myapp.views.async_brotli_view),
    path("myapp/async/cache_hit", myapp.views.async_fake_cache_hit_view),
    path("myapp/async/cache_set", myapp.views.async_fake_cache_set_view),
]
