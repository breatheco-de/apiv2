from django.urls import path

from .views import (
    InfluencerPayoutReportView,
    GeekCreatorPaymentView,
    GeekCreatorCommissionView,
    UserUsageCommissionView,
    GeekCreatorReferralCommissionView,
)

app_name = "commission"

urlpatterns = [
    path("academy/<int:academy_id>/report", InfluencerPayoutReportView.as_view()),
    path(
        "academy/<int:academy_id>/report.<str:extension>",
        InfluencerPayoutReportView.as_view(),
        name="commission_report_by_extension",
    ),
    path("academy/<int:academy_id>/payments", GeekCreatorPaymentView.as_view(), name="payments"),
    path("academy/<int:academy_id>/payments/<int:payment_id>", GeekCreatorPaymentView.as_view(), name="payment_detail"),
    path("academy/<int:academy_id>/commissions", GeekCreatorCommissionView.as_view(), name="commissions"),
    path("academy/<int:academy_id>/usage-commissions", UserUsageCommissionView.as_view(), name="usage_commissions"),
    path(
        "academy/<int:academy_id>/referral-commissions",
        GeekCreatorReferralCommissionView.as_view(),
        name="referral_commissions",
    ),
    path(
        "academy/<int:academy_id>/referral-commissions/<int:commission_id>",
        GeekCreatorReferralCommissionView.as_view(),
        name="referral_commission_detail",
    ),
]
