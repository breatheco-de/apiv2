from django.urls import path
from .views import redirect_link

app_name = "marketing"
urlpatterns = [
    path("<str:link_slug>", redirect_link, name="slug"),
]
