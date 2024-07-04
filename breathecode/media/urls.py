from django.urls.conf import path
from .views import MediaView, CategoryView, UploadView, MaskingUrlView, ResolutionView

media_view = MediaView.as_view({"get": "get", "put": "put", "delete": "delete"})

media_by_id_view = MediaView.as_view({"get": "get_id", "put": "put_id", "delete": "delete_id"})

media_by_slug_view = MediaView.as_view(
    {
        "get": "get_slug",
    }
)

media_by_name_view = MediaView.as_view(
    {
        "get": "get_name",
    }
)

category_view = CategoryView.as_view({"get": "get", "post": "post"})
category_by_id_view = CategoryView.as_view({"get": "get_id"})
category_by_slug_view = CategoryView.as_view({"get": "get_slug", "put": "put", "delete": "delete"})

resolution_by_id_view = ResolutionView.as_view({"get": "get_id", "delete": "delete"})
resolution_by_media_id_view = ResolutionView.as_view({"get": "get_media_id"})

app_name = "media"
urlpatterns = [
    path(
        "",
        media_view,
        name="root",
    ),
    path(
        "info",
        media_view,
        name="info",
    ),
    path(
        "info/<int:media_id>",
        media_by_id_view,
        name="info_id",
    ),
    path(
        "info/<int:media_id>/resolution",
        resolution_by_media_id_view,
        name="info_id_resolution",
    ),
    path(
        "info/<slug:media_slug>",
        media_by_slug_view,
        name="info_slug",
    ),
    path(
        "info/<str:media_name>",
        media_by_name_view,
        name="info_name",
    ),
    path(
        "resolution/<int:resolution_id>",
        resolution_by_id_view,
        name="resolution_id",
    ),
    path(
        "file/<int:media_id>",
        MaskingUrlView.as_view(),
        name="file_id",
    ),
    path(
        "file/<str:media_slug>",
        MaskingUrlView.as_view(),
        name="file_slug",
    ),
    path(
        "upload",
        UploadView.as_view(),
        name="upload",
    ),
    path(
        "category",
        category_view,
        name="category",
    ),
    path(
        "category/<int:category_id>",
        category_by_id_view,
        name="category_id",
    ),
    path(
        "category/<str:category_slug>",
        category_by_slug_view,
        name="category_slug",
    ),
]
