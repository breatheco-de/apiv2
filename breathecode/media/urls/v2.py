from django.urls import path

from ..views import AcademyChunkUploadView, AcademyChunkView, MeChunkUploadView, MeChunkView, OperationTypeView
from .v1 import urlpatterns as urlpatterns_v1

deprecation_list = [
    "upload",
]

app_name = "activity"
urlpatterns = [
    path("operationtype", OperationTypeView.as_view(), name="operationtype"),
    path("operationtype/<str:op_type>", OperationTypeView.as_view(), name="operationtype_type"),
    path("me/chunk", MeChunkView.as_view(), name="me_chunk"),
    path("me/chunk/upload", MeChunkUploadView.as_view(), name="me_chunk_upload"),
    path("academy/chunk", AcademyChunkView.as_view(), name="academy_chunk"),
    path("academy/chunk/upload", AcademyChunkUploadView.as_view(), name="academy_chunk_upload"),
    *[r for r in urlpatterns_v1 if r.pattern._route not in deprecation_list],
]
