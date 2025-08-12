from django.contrib import admin

from .models import CohortInfluencer, InfluencerCommission, InfluencerPayment


@admin.register(CohortInfluencer)
class CohortInfluencerAdmin(admin.ModelAdmin):
    list_display = ("cohort", "influencer", "is_active", "assigned_at")
    list_filter = ("is_active",)
    search_fields = (
        "cohort__slug",
        "cohort__name",
        "influencer__email",
        "influencer__first_name",
        "influencer__last_name",
    )


@admin.register(InfluencerCommission)
class InfluencerCommissionAdmin(admin.ModelAdmin):
    list_display = ("influencer", "cohort", "month", "commission_type", "amount_paid", "currency")
    list_filter = ("commission_type", "month", "currency")
    search_fields = ("influencer__email", "cohort__slug")


@admin.register(InfluencerPayment)
class InfluencerPaymentAdmin(admin.ModelAdmin):
    list_display = ("influencer", "month", "total_amount", "currency", "status", "payment_date")
    list_filter = ("status", "month", "currency")
    search_fields = ("influencer__email",)
