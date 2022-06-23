from django.contrib import admin
from django.urls import path, include
from .views import (AssetView, get_keywords, get_clusters, get_categories, render_readme, get_technologies,
                    get_config, get_translations, handle_test_syllabus, render_preview_html,
                    handle_test_asset, forward_asset_url, get_alias_redirects, AcademyAssetView)

app_name = 'feedback'
urlpatterns = [
    path('asset', AssetView.as_view()),
    path('asset/test', handle_test_asset),
    path('asset/preview/<str:asset_slug>', render_preview_html),
    path('asset/gitpod/<str:asset_slug>', forward_asset_url),
    path('asset/<str:asset_slug>', AssetView.as_view()),
    path('asset/<str:asset_slug>.<str:extension>', render_readme),
    path('asset/<str:asset_slug>/github/config', get_config),
    path('academy/asset', AcademyAssetView.as_view()),
    path('keyword', get_keywords),
    path('keywordcluster', get_clusters),
    path('category', get_categories),
    path('technology', get_technologies),
    path('translation', get_translations),
    path('syllabus/test', handle_test_syllabus),
    path('alias/redirect', get_alias_redirects),
]
