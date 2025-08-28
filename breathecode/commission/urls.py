from django.urls import path

from .views import InfluencerPayoutReportView

app_name = "commission"

urlpatterns = [
    path("academy/<int:academy_id>/report", InfluencerPayoutReportView.as_view()),
    path(
        "academy/<int:academy_id>/report.<str:extension>",
        InfluencerPayoutReportView.as_view(),
        name="commission_report_by_extension",
    ),
]
