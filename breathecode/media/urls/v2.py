from django.urls import path

from ..views import ChunkedUploadView, JoinChunksView, MediaClaimView

from .v1 import urlpatterns as urlpatterns_v1

deprecation_list = [
    'upload',
]

app_name = 'activity'
urlpatterns = [
    path('upload', ChunkedUploadView.as_view(), name='upload'),
    path('upload/<int:file_id>/join', JoinChunksView.as_view(), name='upload_id_join'),
    path('<int:file_id>/claim', MediaClaimView.as_view(), name='id_claim'),
    *[r for r in urlpatterns_v1 if r.pattern._route not in deprecation_list],
]
