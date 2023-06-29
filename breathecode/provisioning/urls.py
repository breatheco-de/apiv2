from django.urls import path

from .views import (AcademyActivityView, UploadView, redirect_new_container, redirect_workspaces)

app_name = 'provisioning'
urlpatterns = [
    path('me/container/new', redirect_new_container),
    path('me/workspaces', redirect_workspaces),
    path('admin/upload', UploadView.as_view(), name='admin_upload'),
    path('academy/activity', AcademyActivityView.as_view(), name='academy_activity'),
    # path('academy/me/container', ContainerMeView.as_view()),
    # path('me/container', ContainerMeView.as_view()),
    # path('me/container/<int:container_id>', ContainerMeView.as_view()),
]
