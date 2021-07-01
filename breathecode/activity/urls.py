from django.urls import path

from .views import ActivityTypeView, ActivityMeView, ActivityClassroomView

app_name = 'activity'
urlpatterns = [
    path('me', ActivityMeView.as_view(), name='root'),
    path('type/', ActivityTypeView.as_view(), name='type'),
    path('type/<str:activity_slug>',
         ActivityTypeView.as_view(),
         name='type_slug'),
    path('cohort/<str:cohort_id>',
         ActivityClassroomView.as_view(),
         name='cohort_id'),
]
