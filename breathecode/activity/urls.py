from django.urls import path

from .views import ActivityTypeView, ActivityView

app_name = 'activity'
urlpatterns = [
    path('', ActivityView.as_view(), name='root'),
    path('type/', ActivityTypeView.as_view(), name='type'),
    path('type/<str:activity_slug>',
         ActivityTypeView.as_view(),
         name='type_slug'),
]
