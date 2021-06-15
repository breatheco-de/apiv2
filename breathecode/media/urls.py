from django.urls import path
from .views import MediaView, CategoryView, UploadView, MaskingUrlView, ResolutionView

app_name='media'
urlpatterns = [
    path('', MediaView.as_view(), name='root'),
    path('info', MediaView.as_view(), name="info"),
    path('info/<int:media_id>', MediaView.as_view(), name='info_id'),
    path('info/<int:media_id>/resolution', ResolutionView.as_view(), name='info_id_resolution'),
    path('info/<slug:media_slug>', MediaView.as_view(), name='info_slug'),
    path('info/<str:media_name>', MediaView.as_view(), name='info_name'),
    path('resolution/<int:resolution_id>', ResolutionView.as_view(), name='resolution_id'),

    path('file/<int:media_id>', MaskingUrlView.as_view(), name='file_id'),
    path('file/<slug:media_slug>', MaskingUrlView.as_view(), name='file_slug'),

    path('upload', UploadView.as_view(), name='upload'),

    path('category', CategoryView.as_view(), name='category'),
    path('category/<int:category_id>', CategoryView.as_view(), name='category_id'),
    path('category/<str:category_slug>', CategoryView.as_view(), name='category_slug'),
]
