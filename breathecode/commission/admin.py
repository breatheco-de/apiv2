from django.contrib import admin

from .models import (
    CohortTeacherInfluencer,
    TeacherInfluencerCommission,
    TeacherInfluencerPayment,
    TeacherInfluencerReferralCommission,
    UserCohortEngagement,
)


@admin.register(CohortTeacherInfluencer)
class CohortTeacherInfluencerAdmin(admin.ModelAdmin):
    list_display = ("cohort", "influencer", "assigned_at", "is_active")
    list_filter = ("is_active",)
    search_fields = ("cohort__slug", "influencer__email")
    raw_id_fields = ("cohort", "influencer")


@admin.register(TeacherInfluencerCommission)
class TeacherInfluencerCommission(admin.ModelAdmin):
    list_display = ("influencer", "cohort", "month", "commission_type", "amount_paid", "currency")
    list_filter = ("commission_type", "month", "currency")
    search_fields = ("influencer__email", "cohort__slug")
    raw_id_fields = ("influencer", "cohort", "currency")


@admin.register(TeacherInfluencerPayment)
class TeacherInfluencerPaymentAdmin(admin.ModelAdmin):
    list_display = ("influencer", "month", "total_amount", "currency", "status", "payment_date")
    list_filter = ("status", "month", "currency")
    search_fields = ("influencer__email",)
    raw_id_fields = ("influencer", "currency", "commissions")


@admin.register(TeacherInfluencerReferralCommission)
class TeacherInfluencerReferralCommissionAdmin(admin.ModelAdmin):
    list_display = (
        "invoice",
        "teacher_influencer",
        "buyer",
        "academy",
        "amount",
        "currency",
        "status",
        "available_at",
        "matured_at",
        "created_at",
    )
    list_filter = ("currency", "status")
    search_fields = ("influencer__email", "buyer__email", "invoice__id")
    raw_id_fields = ("invoice", "teacher_influencer", "buyer", "academy", "currency")


@admin.register(UserCohortEngagement)
class UserCohortEngagementAdmin(admin.ModelAdmin):
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
