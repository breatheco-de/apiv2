from django.urls import path
from .views import forward_asset_url, handle_internal_link

app_name = "registry"
urlpatterns = [
    path("internal-link", handle_internal_link, name="handle_internal_link"),
    path("<slug:asset_slug>", forward_asset_url),
]
