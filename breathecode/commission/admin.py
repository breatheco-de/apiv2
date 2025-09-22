from django.contrib import admin
from django.utils.html import format_html

from .models import (
    GeekCreatorCohort,
    GeekCreatorCommission,
    GeekCreatorPayment,
    GeekCreatorReferralCommission,
    UserUsageCommission,
)


@admin.register(GeekCreatorCohort)
class GeekCreatorCohortAdmin(admin.ModelAdmin):
    list_display = ("cohort", "influencer", "assigned_at", "is_active")
    list_filter = ("is_active",)
    search_fields = ("cohort__slug", "influencer__email")
    raw_id_fields = ("cohort", "influencer")


@admin.register(GeekCreatorCommission)
class GeekCreatorCommission(admin.ModelAdmin):
    list_display = (
        "influencer",
        "cohort",
        "month",
        "commission_type",
        "amount_paid",
        "currency",
        "num_users",
        "get_usage_count",
        "get_referral_count",
    )
    list_filter = ("commission_type", "month", "currency")
    search_fields = ("influencer__email", "cohort__slug")
    raw_id_fields = ("influencer", "cohort", "currency")

    def get_usage_count(self, obj):
        """Get count of usage commissions."""
        count = obj.usage_commissions.count()
        if count > 0:
            return format_html(f"<span class='badge bg-info'>{count}</span>")
        return format_html("<span class='badge'>0</span>")

    get_usage_count.short_description = "Usage Count"

    def get_referral_count(self, obj):
        """Get count of referral commissions."""
        count = obj.referral_commissions.count()
        if count > 0:
            return format_html(f"<span class='badge bg-success'>{count}</span>")
        return format_html("<span class='badge'>0</span>")

    get_referral_count.short_description = "Referral Count"


@admin.register(GeekCreatorPayment)
class GeekCreatorPaymentAdmin(admin.ModelAdmin):
    list_display = ("influencer", "month", "total_amount", "currency", "status", "payment_date", "get_status_text")
    list_filter = ("status", "month", "currency")
    search_fields = ("influencer__email",)
    raw_id_fields = ("influencer", "currency", "commissions")
    fields = (
        "influencer",
        "month",
        "total_amount",
        "currency",
        "status",
        "status_text",
        "payment_date",
        "commissions",
    )

    def get_status_text(self, obj):
        """Display status text with formatting."""
        if obj.status_text:
            return format_html(f"<span style='color: orange;'>{obj.status_text}</span>")
        return "-"

    get_status_text.short_description = "Status Info"


@admin.register(GeekCreatorReferralCommission)
class GeekCreatorReferralCommissionAdmin(admin.ModelAdmin):
    list_display = (
        "invoice",
        "geek_creator",
        "buyer",
        "academy",
        "amount",
        "currency",
        "status",
        "available_at",
        "created_at",
    )
    list_filter = ("currency", "status", "created_at")
    search_fields = ("geek_creator__email", "buyer__email", "invoice__id")
    raw_id_fields = ("invoice", "geek_creator", "buyer", "academy", "currency")
    fields = (
        "invoice",
        "geek_creator",
        "academy",
        "buyer",
        "amount",
        "currency",
        "status",
        "available_at",
        "created_at",
        "status_text",
    )


@admin.register(UserUsageCommission)
class UserUsageCommissionAdmin(admin.ModelAdmin):
    list_display = (
        "influencer",
        "user",
        "cohort",
        "academy",
        "month",
        "user_total_points",
        "cohort_points",
        "paid_amount",
        "commission_amount",
        "currency",
    )
    list_filter = ("month", "currency")
    search_fields = ("influencer__email", "user__email", "cohort__slug")
    raw_id_fields = ("influencer", "user", "cohort", "academy", "currency")
