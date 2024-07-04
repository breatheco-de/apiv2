from django.urls import path
from .views import forward_asset_url

app_name = "registry"
urlpatterns = [
    path("<slug:asset_slug>", forward_asset_url),
]
