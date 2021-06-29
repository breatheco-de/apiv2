from django.urls import path

from .views import CleanView, LoadFixtureView, LoadRolesView, ResetView, MixerView

app_name = 'events'
urlpatterns = [
    path('load/fixtures', LoadFixtureView.as_view(), name='load_fixtures'),
    path('load/roles', LoadRolesView.as_view(), name='load_roles'),
    path('mixer', MixerView.as_view(), name='mixer'),
    path('mixer/<int:how_many>', MixerView.as_view(), name='mixer_count'),
    path('mixer/<str:model_name>', MixerView.as_view(), name='mixer_model'),
    path('mixer/<str:model_name>/<int:how_many>',
         MixerView.as_view(),
         name='mixer_model_count'),
    path('reset', ResetView.as_view(), name='reset'),
    path('clean', CleanView.as_view(), name='clean'),
    path('clean/<str:model_name>', CleanView.as_view(), name='clean_model'),
]
