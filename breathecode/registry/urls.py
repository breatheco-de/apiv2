from django.contrib import admin
from django.urls import path, include
from .views import GetAssetView, redirect_gitpod

app_name='feedback'
urlpatterns = [
    path('asset', GetAssetView.as_view()),
    path('asset/<str:asset_slug>', GetAssetView.as_view()),
    path('asset/gitpod/<str:asset_slug>', redirect_gitpod),
]

