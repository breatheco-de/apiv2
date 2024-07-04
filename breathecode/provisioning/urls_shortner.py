from django.urls import path
from .views import redirect_new_container_public

app_name = "provisioning"
urlpatterns = [
    path("", redirect_new_container_public),
]
