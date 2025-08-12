from django.core.exceptions import ValidationError
from django.db import models


class CohortInfluencer(models.Model):
    cohort = models.ForeignKey("admissions.Cohort", on_delete=models.CASCADE)
    influencer = models.ForeignKey("auth.User", on_delete=models.CASCADE)
    assigned_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    referral_share = models.FloatField(
        null=True,
        blank=True,
        help_text=("Override of revenue share (%) for users who joined because of this cohort (first month)"),
    )
    usage_share = models.FloatField(
        null=True,
        blank=True,
        help_text=("Override of revenue share (%) for active users from unrelated cohorts"),
    )

    class Meta:
        unique_together = ("cohort", "influencer")

    def clean(self):
        for field in ["referral_share", "usage_share"]:
            value = getattr(self, field)
            if value is not None and not (0 <= value <= 100):
                raise ValidationError({field: "Must be between 0 and 100."})


class InfluencerCommission(models.Model):
    class CommissionType(models.TextChoices):
        REFERRAL = "REFERRAL", "Referral"
        USAGE = "USAGE", "Usage"

    influencer = models.ForeignKey("auth.User", on_delete=models.CASCADE)
    cohort = models.ForeignKey("admissions.Cohort", on_delete=models.CASCADE, null=True, blank=True)
    month = models.DateField(help_text="Month (YYYY-MM-01) for the commission period", db_index=True)
    commission_type = models.CharField(max_length=10, choices=CommissionType, db_index=True)

    amount_paid = models.FloatField(default=0.0)
    currency = models.ForeignKey("payments.Currency", on_delete=models.CASCADE)
    num_users = models.IntegerField(default=0)
    details = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        unique_together = ("influencer", "cohort", "month", "commission_type")


class InfluencerPayment(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PAID = "PAID", "Paid"

    influencer = models.ForeignKey("auth.User", on_delete=models.CASCADE)
    month = models.DateField(db_index=True)
    total_amount = models.FloatField(default=0.0)
    currency = models.ForeignKey("payments.Currency", on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=Status, default=Status.PENDING, db_index=True)
    payment_date = models.DateTimeField(null=True, blank=True)

    commissions = models.ManyToManyField(InfluencerCommission, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)
