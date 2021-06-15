from django.urls import path

from .views import ActivityTypeView, ActivityView, UserActivityView

app_name = 'activity'
urlpatterns = [
    path('', ActivityView.as_view(), name='root'),
    path('type/', ActivityTypeView.as_view(), name='type'),
    path('user/<int:user_id>', UserActivityView.as_view(), name='user_id'),
    path('user/<str:email>', UserActivityView.as_view(), name='user_email'),
]
