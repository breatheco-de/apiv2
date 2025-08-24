from django.urls import path

from .views import InfluencerPayoutReportView

app_name = "commission"

urlpatterns = [
    path("report", InfluencerPayoutReportView.as_view()),
]
