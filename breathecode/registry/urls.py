from django.contrib import admin
from django.urls import path, include
from .views import AssetView, redirect_gitpod, get_readme, get_technologies, get_config

app_name = 'feedback'
urlpatterns = [
    path('asset', AssetView.as_view()),
    path('technology', get_technologies),
    path('asset/<str:asset_slug>', AssetView.as_view()),
    path('asset/gitpod/<str:asset_slug>', redirect_gitpod),
    path('asset/readme/<str:asset_slug>', get_readme),
    path('asset/<str:asset_slug>/github/config', get_config),
]
