from django.urls import path

from ..views import V2MeActivityView

from .v1 import urlpatterns as urlpatterns_v1

deprecation_list = [
    'me',
    'type',
    'type/<str:activity_slug>',
]

app_name = 'activity'
urlpatterns = [
    *[r for r in urlpatterns_v1 if r.pattern._route not in deprecation_list],
    path('me/activity', V2MeActivityView.as_view(), name='me_activity'),
    path('me/activity/<int:activity_id>', V2MeActivityView.as_view(), name='me_activity_id'),
    path('academy/activity', V2MeActivityView.as_view(), name='academy_activity'),
    path('academy/activity/<int:activity_id>', V2MeActivityView.as_view(), name='academy_activity_id'),
]
