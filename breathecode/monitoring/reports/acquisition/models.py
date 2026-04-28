"""Stored rows for the acquisition monitoring report."""

from django.contrib.auth.models import User
from django.db import models

from breathecode.admissions.models import Academy


class AcquisitionReport(models.Model):
    """One row per FormEntry/UserInvite acquisition event."""

    class SourceType(models.TextChoices):
        FORM_ENTRY = "FORM_ENTRY", "Form entry"
        USER_INVITE = "USER_INVITE", "User invite"

    class FunnelTier(models.IntegerChoices):
        WON_OR_SALE = 1, "won_or_sale"
        STRONG_LEAD = 2, "strong_lead"
        SOFT_LEAD = 3, "soft_lead"
        NURTURE_INVITE = 4, "nurture_invite"

    source_type = models.CharField(max_length=20, choices=SourceType.choices)
    source_id = models.PositiveIntegerField()
    report_date = models.DateField(db_index=True)

    academy = models.ForeignKey(Academy, on_delete=models.CASCADE, related_name="acquisition_reports")
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="acquisition_reports",
    )
    email = models.CharField(max_length=150, blank=True, default="")

    funnel_tier = models.PositiveSmallIntegerField(choices=FunnelTier.choices, db_index=True)

    utm_source = models.CharField(max_length=70, null=True, blank=True)
    utm_medium = models.CharField(max_length=70, null=True, blank=True)
    utm_campaign = models.CharField(max_length=70, null=True, blank=True)
    utm_term = models.CharField(max_length=50, null=True, blank=True)
    utm_content = models.CharField(max_length=70, null=True, blank=True)
    utm_placement = models.CharField(max_length=50, null=True, blank=True)
    landing_url = models.CharField(max_length=2000, null=True, blank=True)
    conversion_url = models.CharField(max_length=2000, null=True, blank=True)

    lead_type = models.CharField(max_length=15, null=True, blank=True)
    deal_status = models.CharField(max_length=15, null=True, blank=True)
    attribution_id = models.CharField(max_length=30, null=True, blank=True)

    event_slug = models.SlugField(max_length=120, null=True, blank=True)
    asset_slug = models.SlugField(max_length=60, null=True, blank=True)
    course = models.ForeignKey(
        "marketing.Course",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="acquisition_reports",
    )
    cohort = models.ForeignKey(
        "admissions.Cohort",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="acquisition_reports",
    )
    syllabus = models.ForeignKey(
        "admissions.Syllabus",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="acquisition_reports",
    )
    role = models.ForeignKey(
        "authenticate.Role",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="acquisition_reports",
    )
    author = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="authored_acquisition_reports",
    )

    subscription_seat = models.ForeignKey(
        "payments.SubscriptionSeat",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="acquisition_reports",
    )
    plan_financing_seat = models.ForeignKey(
        "payments.PlanFinancingSeat",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="acquisition_reports",
    )
    payment_method = models.ForeignKey(
        "payments.PaymentMethod",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="acquisition_reports",
    )
    team_seat_invite = models.BooleanField(default=False)

    details = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["source_type", "source_id"],
                name="monitoring_acquisition_report_source_uniq",
            ),
        ]
        indexes = [
            models.Index(fields=["academy", "report_date", "source_type"]),
            models.Index(fields=["report_date", "-created_at"]),
            models.Index(fields=["utm_source", "report_date"]),
            models.Index(fields=["asset_slug", "report_date"]),
            models.Index(fields=["event_slug", "report_date"]),
            models.Index(fields=["conversion_url", "report_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.source_type}:{self.source_id} on {self.report_date}"
