from django.urls import path

from ..views import V3AcademyActivityView, V3ActivityKindView

app_name = "activity"
urlpatterns = [
    path("kinds", V3ActivityKindView.as_view(), name="kinds"),
    path("academy/activity", V3AcademyActivityView.as_view(), name="academy_activity"),
    path("academy/activity/<str:activity_id>", V3AcademyActivityView.as_view(), name="academy_activity_id"),
]

