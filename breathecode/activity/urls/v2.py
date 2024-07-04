from django.urls import path

from ..views import V2AcademyActivityView, V2MeActivityView, V2AcademyActivityReportView

from .v1 import urlpatterns as urlpatterns_v1

deprecation_list = [
    "me",
    "type",
    "type/<str:activity_slug>",
]

app_name = "activity"
urlpatterns = [
    path("me/activity", V2MeActivityView.as_view(), name="me_activity"),
    path("me/activity/<str:activity_id>", V2MeActivityView.as_view(), name="me_activity_id"),
    path("academy/activity", V2AcademyActivityView.as_view(), name="academy_activity"),
    path("academy/activity/<str:activity_id>", V2AcademyActivityView.as_view(), name="academy_activity_id"),
    path("report", V2AcademyActivityReportView.as_view(), name="report"),
    *[r for r in urlpatterns_v1 if r.pattern._route not in deprecation_list],
]
