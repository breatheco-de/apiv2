from django.urls import path

from .views import CleanView, LoadRolesView, MixerView

app_name = "events"
urlpatterns = [
    path("load/roles", LoadRolesView.as_view(), name="load_roles"),
    path("mixer", MixerView.as_view(), name="mixer"),
    path("clean", CleanView.as_view(), name="clean"),
    path("clean/<str:model_name>", CleanView.as_view(), name="clean_model"),
]
