from django.db import models
from django.utils import timezone


class CohortTeacherInfluencer(models.Model):
    cohort = models.ForeignKey("admissions.Cohort", on_delete=models.CASCADE)
    influencer = models.ForeignKey("auth.User", on_delete=models.CASCADE)
    assigned_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("cohort", "influencer")


class TeacherInfluencerCommission(models.Model):
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
        unique_together = ("influencer", "cohort", "month", "commission_type", "currency")


class TeacherInfluencerPayment(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PAID = "PAID", "Paid"

    influencer = models.ForeignKey("auth.User", on_delete=models.CASCADE)
    month = models.DateField(db_index=True)
    total_amount = models.FloatField(default=0.0)
    currency = models.ForeignKey("payments.Currency", on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=Status, default=Status.PENDING, db_index=True)
    payment_date = models.DateTimeField(null=True, blank=True)

    commissions = models.ManyToManyField(TeacherInfluencerCommission, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)


class TeacherInfluencerReferralCommission(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PAID = "PAID", "Paid"
        CANCELLED = "CANCELLED", "Cancelled"

    invoice = models.OneToOneField(
        "payments.Invoice",
        on_delete=models.CASCADE,
        related_name="influencer_referral_record",
        help_text="Related paid invoice",
    )
    teacher_influencer = models.ForeignKey("auth.User", on_delete=models.CASCADE)
    academy = models.ForeignKey("admissions.Academy", on_delete=models.CASCADE)
    buyer = models.ForeignKey(
        "auth.User",
        on_delete=models.CASCADE,
        related_name="influencer_referred_buys",
        help_text="the person that paid and used the referral coupon",
    )
    amount = models.FloatField(default=0.0)
    currency = models.ForeignKey("payments.Currency", on_delete=models.CASCADE)

    status = models.CharField(max_length=10, choices=Status, default=Status.PENDING, db_index=True)
    available_at = models.DateTimeField(help_text="Date when this referral becomes eligible (e.g., paid_at + 30d)")
    status_text = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now, editable=True)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self) -> str:
        return f"ReferralRecord invoice={self.invoice_id} influencer={self.teacher_influencer_id} buyer={self.buyer_id}"

    @property
    def is_matured(self) -> bool:
        """Check if the referral is matured based on available_at date."""
        from django.utils import timezone

        return timezone.now() >= self.available_at


class UserCohortEngagement(models.Model):
    """Monthly engagement snapshot for a user in a cohort of a teacher influencer.

    One row per (influencer, user, cohort, month, currency) when the user had activity in that cohort.
    """

    influencer = models.ForeignKey("auth.User", on_delete=models.CASCADE)
    user = models.ForeignKey("auth.User", on_delete=models.CASCADE, related_name="teacher_influencer_engagements")
    month = models.DateField(db_index=True, help_text="Month (YYYY-MM-01)")

    cohort = models.ForeignKey("admissions.Cohort", on_delete=models.CASCADE)
    academy = models.ForeignKey("admissions.Academy", on_delete=models.CASCADE)

    user_total_points = models.FloatField(default=0.0)
    cohort_points = models.FloatField(default=0.0)

    paid_amount = models.FloatField(default=0.0)
    currency = models.ForeignKey("payments.Currency", on_delete=models.CASCADE)
    commission_amount = models.FloatField(default=0.0)

    details = models.JSONField(default=dict, blank=True, help_text="Activity breakdown and metadata")

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        unique_together = ("influencer", "user", "cohort", "month", "currency")
