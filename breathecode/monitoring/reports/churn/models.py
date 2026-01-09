"""Churn risk report models."""

from django.contrib.auth.models import User
from django.db import models

from breathecode.admissions.models import Academy


class ChurnRiskReport(models.Model):
    """Daily per-user churn risk assessment."""

    class RiskLevel(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"
        CRITICAL = "CRITICAL", "Critical"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="churn_reports")
    academy = models.ForeignKey(
        Academy,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="churn_reports",
    )
    report_date = models.DateField(db_index=True)

    # Core risk metrics
    churn_risk_score = models.FloatField(help_text="0-100, higher = more likely to churn")
    risk_level = models.CharField(max_length=10, choices=RiskLevel.choices, db_index=True)

    # Key signals (pre-computed for fast queries)
    days_since_last_activity = models.IntegerField(default=0)
    login_count_7d = models.IntegerField(default=0)
    login_trend = models.FloatField(default=0, help_text="Percentage change vs previous 7 days")
    assignments_completed_7d = models.IntegerField(default=0)
    assignment_trend = models.FloatField(default=0, help_text="Percentage change vs previous 7 days")
    avg_frustration_score = models.FloatField(null=True, blank=True)
    avg_engagement_score = models.FloatField(null=True, blank=True)

    # Subscription context
    subscription_status = models.CharField(max_length=20, null=True, blank=True)
    days_until_renewal = models.IntegerField(null=True, blank=True)
    has_payment_issues = models.BooleanField(default=False)

    # Full breakdown for debugging/analysis
    details = models.JSONField(default=dict, help_text="Detailed metrics breakdown")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [["user", "report_date"]]
        indexes = [
            models.Index(fields=["academy", "report_date", "risk_level"]),
            models.Index(fields=["risk_level", "report_date"]),
            models.Index(fields=["-churn_risk_score"]),
            models.Index(fields=["report_date", "-churn_risk_score"]),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.report_date} - {self.risk_level}"


class ChurnAlert(models.Model):
    """Triggered when user crosses risk thresholds."""

    class AlertType(models.TextChoices):
        INACTIVITY = "INACTIVITY", "Inactive for 7+ days"
        ENGAGEMENT_DROP = "ENGAGEMENT_DROP", "Engagement dropped significantly"
        HIGH_FRUSTRATION = "HIGH_FRUSTRATION", "High frustration detected"
        PAYMENT_RISK = "PAYMENT_RISK", "Payment issues"
        TRIAL_EXPIRING = "TRIAL_EXPIRING", "Trial expiring without conversion"

    class Severity(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"
        CRITICAL = "CRITICAL", "Critical"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="churn_alerts")
    academy = models.ForeignKey(
        Academy,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="churn_alerts",
    )
    alert_type = models.CharField(max_length=30, choices=AlertType.choices)
    severity = models.CharField(max_length=10, choices=Severity.choices)

    triggered_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    action_taken = models.TextField(null=True, blank=True, help_text="What intervention was done")

    # Snapshot of metrics when alert was triggered
    metrics_snapshot = models.JSONField(default=dict)

    class Meta:
        indexes = [
            models.Index(fields=["academy", "severity", "-triggered_at"]),
            models.Index(fields=["user", "-triggered_at"]),
            models.Index(fields=["alert_type", "-triggered_at"]),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.alert_type} ({self.severity})"

