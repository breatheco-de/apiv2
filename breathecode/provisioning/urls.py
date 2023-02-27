from django.urls import path

from .views import (
    ContainerMeView, )

app_name = 'provisioning'
urlpatterns = [
    path('me/container', ContainerMeView.as_view()),
    # path('me/<slug:plan_slug>', PlanView.as_view()),
]
