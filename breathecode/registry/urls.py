from django.contrib import admin
from django.urls import path, include
from .views import (
    AssetView,
    render_readme,
    get_technologies,
    get_config,
    get_translations,
    handle_test_syllabus,
    render_preview_html,
    handle_test_asset,
)

app_name = 'feedback'
urlpatterns = [
    path('asset', AssetView.as_view()),
    path('technology', get_technologies),
    path('translation', get_translations),
    path('syllabus/test', handle_test_syllabus),
    path('asset/test', handle_test_asset),
    path('asset/<str:asset_slug>', AssetView.as_view()),
    path('asset/readme/<str:asset_slug>', render_readme),
    path('asset/preview/<str:asset_slug>', render_preview_html),
    path('asset/<str:asset_slug>/github/config', get_config),
]
