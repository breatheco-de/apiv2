from django.contrib import admin

from .models import (
    TeacherInfluencerCommission,
    TeacherInfluencerPayment,
    TeacherInfluencerReferralCommission,
    UserCohortEngagement,
)


@admin.register(TeacherInfluencerCommission)
class TeacherInfluencerCommission(admin.ModelAdmin):
    list_display = ("influencer", "cohort", "month", "commission_type", "amount_paid", "currency")
    list_filter = ("commission_type", "month", "currency")
    search_fields = ("influencer__email", "cohort__slug")


@admin.register(TeacherInfluencerPayment)
class TeacherInfluencerPaymentAdmin(admin.ModelAdmin):
    list_display = ("influencer", "month", "total_amount", "currency", "status", "payment_date")
    list_filter = ("status", "month", "currency")
    search_fields = ("influencer__email",)


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
