"""
URL Configuration for Commission App

This module defines URL patterns following REST conventions with some specific exceptions
for the BreatheCode API v2.

REST Naming Conventions:
========================

1. Resource-based URLs:
   - Use plural nouns for collections: /academy/payments, /academy/commissions
   - Use singular nouns for individual resources: /payment/<id>

2. HTTP Methods:
   - GET /academy/<id>/payments - List all academy payments
   - POST /academy/<id>/payments - Create new payment
   - GET /academy/<id>/payments/<id> - Get specific payment
   - PUT/PATCH /academy/<id>/payments/<id> - Update specific payment
   - DELETE /academy/<id>/payments/<id> - Delete specific payment

3. Nested Resources:
   - /academy/<id>/report - Commission reports for specific academy
   - /academy/<id>/payments/<id> - Specific payment for academy
   - /academy/<id>/commissions - Commissions for specific academy
   - /academy/<id>/usage-commissions - Usage commissions for academy
   - /academy/<id>/referral-commissions - Referral commissions for academy

4. Actions (Non-REST exceptions):
   - /academy/<id>/report - Generate commission report (GET)
   - /academy/<id>/report.<extension> - Export report in specific format (GET)

5. Special Endpoints:
   - /academy/<id>/* - Academy-specific commission resources
   - Report endpoints with file extensions for exports

6. URL Naming:
   - Use snake_case for URL names: commission_report_by_extension
   - Include resource type and ID when applicable
   - Be descriptive but concise

Examples:
- commission_report_by_extension - Export commission report in specific format
- payments - Academy payments management
- payment_detail - Specific payment details
- commissions - Academy commissions management
- usage_commissions - Usage-based commissions
- referral_commissions - Referral commissions management
"""

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
