from django.urls import path

from .views import InfluencerPayoutReportView


urlpatterns = [
    path("report", InfluencerPayoutReportView.as_view()),
]
