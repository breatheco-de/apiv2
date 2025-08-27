from django.db import models
from django.utils import timezone


class GeekCreatorCohort(models.Model):
    cohort = models.ForeignKey(
        "admissions.Cohort", on_delete=models.CASCADE, help_text="The cohort where the influencer is assigned"
    )
    influencer = models.ForeignKey(
        "auth.User", on_delete=models.CASCADE, help_text="The geek creator assigned to this cohort"
    )
    assigned_at = models.DateTimeField(auto_now_add=True, help_text="When the influencer was assigned to this cohort")
    is_active = models.BooleanField(default=True, help_text="Whether this influencer is currently active")

    class Meta:
        unique_together = ("cohort", "influencer")


class GeekCreatorCommission(models.Model):
    class CommissionType(models.TextChoices):
        REFERRAL = "REFERRAL", "Referral"
        USAGE = "USAGE", "Usage"

    influencer = models.ForeignKey(
        "auth.User", on_delete=models.CASCADE, help_text="The geek creator who earned this commission"
    )
    cohort = models.ForeignKey(
        "admissions.Cohort",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="The cohort related to this commission (null for referral commissions)",
    )
    month = models.DateField(help_text="Month (YYYY-MM-01) for the commission period", db_index=True)
    commission_type = models.CharField(
        max_length=10, choices=CommissionType, db_index=True, help_text="Type of commission: referral or usage"
    )

    amount_paid = models.FloatField(default=0.0, help_text="Total amount paid for this commission")
    currency = models.ForeignKey(
        "payments.Currency", on_delete=models.CASCADE, help_text="Currency of the commission amount"
    )
    num_users = models.IntegerField(default=0, help_text="Number of users involved in this commission")
    details = models.JSONField(
        default=dict, blank=True, help_text="Additional details and metadata about the commission"
    )

    usage_commissions = models.ManyToManyField(
        "UserUsageCommission",
        blank=True,
        related_name="aggregated_usage_commissions",
        help_text="Individual usage commission records included in this commission",
    )
    referral_commissions = models.ManyToManyField(
        "GeekCreatorReferralCommission",
        blank=True,
        related_name="aggregated_referral_commissions",
        help_text="Individual referral commission records included in this commission",
    )

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        unique_together = ("influencer", "cohort", "month", "commission_type", "currency")


class GeekCreatorPayment(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PAID = "PAID", "Paid"

    influencer = models.ForeignKey(
        "auth.User", on_delete=models.CASCADE, help_text="The geek creator receiving this payment"
    )
    month = models.DateField(db_index=True, help_text="Month (YYYY-MM-01) for the payment period")
    total_amount = models.FloatField(default=0.0, help_text="Total amount to be paid for this month")
    currency = models.ForeignKey(
        "payments.Currency", on_delete=models.CASCADE, help_text="Currency of the payment amount"
    )
    status = models.CharField(
        max_length=10, choices=Status, default=Status.PENDING, db_index=True, help_text="Current status of the payment"
    )
    payment_date = models.DateTimeField(null=True, blank=True, help_text="When the payment was actually made")

    commissions = models.ManyToManyField(
        GeekCreatorCommission, blank=True, help_text="Commissions included in this payment"
    )

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)


class GeekCreatorReferralCommission(models.Model):
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
    geek_creator = models.ForeignKey(
        "auth.User", on_delete=models.CASCADE, help_text="The geek creator who made the referral"
    )
    academy = models.ForeignKey(
        "admissions.Academy", on_delete=models.CASCADE, help_text="The academy where the referral was made"
    )
    buyer = models.ForeignKey(
        "auth.User",
        on_delete=models.CASCADE,
        related_name="influencer_referred_buys",
        help_text="The person that paid and used the referral coupon",
    )
    amount = models.FloatField(default=0.0, help_text="Commission amount earned from this referral")
    currency = models.ForeignKey(
        "payments.Currency", on_delete=models.CASCADE, help_text="Currency of the referral commission"
    )

    status = models.CharField(
        max_length=10,
        choices=Status,
        default=Status.PENDING,
        db_index=True,
        help_text="Current status of the referral commission",
    )
    available_at = models.DateTimeField(help_text="Date when this referral becomes eligible (e.g., paid_at + 30d)")
    status_text = models.TextField(null=True, blank=True, help_text="Additional text describing the status")

    created_at = models.DateTimeField(default=timezone.now, editable=True)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self) -> str:
        return f"ReferralRecord invoice={self.invoice_id} influencer={self.geek_creator_id} buyer={self.buyer_id}"

    @property
    def is_matured(self) -> bool:
        """Check if the referral is matured based on available_at date."""
        from django.utils import timezone

        return timezone.now() >= self.available_at


class UserUsageCommission(models.Model):
    """Monthly usage commission snapshot for a user in a cohort of a geek creator.

    One row per (influencer, user, cohort, month, currency) when the user had activity in that cohort.
    """

    influencer = models.ForeignKey(
        "auth.User",
        on_delete=models.CASCADE,
        help_text="The geek creator who will receive commission from this user's activity",
    )
    user = models.ForeignKey(
        "auth.User",
        on_delete=models.CASCADE,
        related_name="geek_creator_engagements",
        help_text="The user whose activity generates commission",
    )
    month = models.DateField(db_index=True, help_text="Month (YYYY-MM-01) for the commission period")

    cohort = models.ForeignKey(
        "admissions.Cohort", on_delete=models.CASCADE, help_text="The cohort where the user had activity"
    )
    academy = models.ForeignKey(
        "admissions.Academy", on_delete=models.CASCADE, help_text="The academy where the activity occurred"
    )

    user_total_points = models.FloatField(
        default=0.0, help_text="Total engagement points earned by the user across all cohorts"
    )
    cohort_points = models.FloatField(
        default=0.0, help_text="Engagement points earned by the user in this specific cohort"
    )

    paid_amount = models.FloatField(default=0.0, help_text="Total amount paid by the user for services")
    currency = models.ForeignKey(
        "payments.Currency", on_delete=models.CASCADE, help_text="Currency of the paid amount and commission"
    )
    commission_amount = models.FloatField(
        default=0.0, help_text="Commission amount earned by the influencer from this user's activity"
    )

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        unique_together = ("influencer", "user", "cohort", "month", "currency")
