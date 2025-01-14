from django.urls import path

from .views import AppUserView, GenericView

app_name = "works"
urlpatterns = [
    path("app/user", AppUserView.as_view(), name="app_user"),
    path("generic", GenericView.as_view(), name="generic"),
]
