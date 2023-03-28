from django.urls import path

from .views import (redirect_new_container, redirect_workspaces)

app_name = 'provisioning'
urlpatterns = [
    path('me/container/new', redirect_new_container),
    path('me/workspaces', redirect_workspaces),
    # path('academy/me/container', ContainerMeView.as_view()),
    # path('me/container', ContainerMeView.as_view()),
    # path('me/container/<int:container_id>', ContainerMeView.as_view()),
]
