from django.urls import path

from ..views import V2AcademyAssetView
from .v1 import urlpatterns as urlpatterns_v1

deprecation_list = [
    "academy/asset/<str:asset_slug>",
]

app_name = "activity"
urlpatterns = [
    path("academy/asset/<str:asset_slug>", V2AcademyAssetView.as_view(), name="academy_asset_slug"),
    *[r for r in urlpatterns_v1 if r.pattern._route not in deprecation_list],
]
