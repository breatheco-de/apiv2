from django.urls import path

from .views import CleanView, LoadFixtureView, LoadRolesView, ResetView

app_name = 'events'
urlpatterns = [
    path('load', LoadFixtureView.as_view(), name='load'),
    path('load/roles', LoadRolesView.as_view(), name='load_roles'),
    path('reset', ResetView.as_view(), name='reset'),
    path('clean', CleanView.as_view(), name='clean'),
]
