from django.contrib import admin
from django.urls import path, include
from .views import GetAssetView, redirect_gitpod, get_readme, get_technologies, get_config

app_name = 'feedback'
urlpatterns = [
    path('asset', GetAssetView.as_view()),
    path('technology', get_technologies),
    path('asset/<str:asset_slug>', GetAssetView.as_view()),
    path('asset/gitpod/<str:asset_slug>', redirect_gitpod),
    path('asset/readme/<str:asset_slug>', get_readme),
    path('asset/<str:asset_slug>/github/config', get_config),
]
