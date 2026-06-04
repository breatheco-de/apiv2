"""Churn risk report generation logic."""

from datetime import date, timedelta
from typing import Any, Optional

from google.cloud import bigquery

from breathecode.activity.models import ACTIVITY_TABLE_NAME
from breathecode.payments.models import Subscription
from breathecode.services.google_cloud import BigQuery

from ..base import BaseReport
from .models import ChurnAlert, ChurnRiskReport


def calculate_churn_risk(metrics: dict) -> tuple[float, str]:
    """
    Calculate churn risk score and level.

    Args:
        metrics: Dictionary of user activity metrics

    Returns:
        Tuple of (risk_score, risk_level)
    """
    weights = {
        "inactivity": 0.25,
        "engagement_decay": 0.20,
        "frustration": 0.15,
        "login_decay": 0.15,
        "assignment_stall": 0.15,
        "payment_issues": 0.10,
    }

    scores = {}

    # Inactivity (days since last activity)
    days_inactive = metrics.get("days_since_last_activity", 0) or 0
    scores["inactivity"] = min(days_inactive / 14 * 100, 100)  # Max risk at 14 days

    # Engagement decay (% drop from baseline)
    engagement_trend = metrics.get("engagement_trend", 0) or 0
    scores["engagement_decay"] = max(-engagement_trend, 0)  # Only penalize drops

    # Frustration level
    scores["frustration"] = metrics.get("avg_frustration_score", 0) or 0

    # Login decay
    login_trend = metrics.get("login_trend", 0) or 0
    scores["login_decay"] = max(-login_trend * 2, 0)  # Amplify login drops

    # Assignment stall
    assignment_trend = metrics.get("assignment_trend", 0) or 0
    scores["assignment_stall"] = max(-assignment_trend * 10, 0)

    # Payment issues
    scores["payment_issues"] = 100 if metrics.get("has_payment_issues") else 0

    # Weighted sum
    risk_score = sum(scores[k] * weights[k] for k in weights)
    risk_score = min(max(risk_score, 0), 100)

    # Determine level
    if risk_score >= 75:
        level = ChurnRiskReport.RiskLevel.CRITICAL
    elif risk_score >= 50:
        level = ChurnRiskReport.RiskLevel.HIGH
    elif risk_score >= 25:
        level = ChurnRiskReport.RiskLevel.MEDIUM
    else:
        level = ChurnRiskReport.RiskLevel.LOW

    return risk_score, level


def fetch_activity_metrics_batch(user_ids: list[int], report_date: date) -> dict[int, dict[str, Any]]:
    """
    Fetch activity metrics from BigQuery for all users in one query.

    Args:
        user_ids: List of user IDs to fetch metrics for
        report_date: The date to generate the report for

    Returns:
        Dictionary mapping user_id to their metrics
    """
    if not user_ids:
        return {}

    client, project_id, dataset = BigQuery.client()

    end_date = report_date + timedelta(days=1)
    start_7d = report_date - timedelta(days=7)
    start_14d = report_date - timedelta(days=14)

    query = f"""
    WITH user_activities AS (
        SELECT
            CAST(user_id AS INT64) AS user_id,
            kind,
            timestamp,
            SAFE_CAST(meta.cohort AS INT64) as cohort_id,
            SAFE_CAST(meta.academy AS INT64) as academy_id
        FROM `{project_id}.{dataset}.{ACTIVITY_TABLE_NAME}`
        WHERE user_id IN UNNEST(@user_ids)
          AND timestamp >= @start_14d
          AND timestamp < @end_date
    ),

    last_7_days AS (
        SELECT
            user_id,
            COUNTIF(kind = 'login') as login_count,
            COUNTIF(kind IN ('assignment_status_updated', 'assignment_review_status_updated')) as assignments_completed,
            MAX(timestamp) as last_activity
        FROM user_activities
        WHERE timestamp >= @start_7d
        GROUP BY user_id
    ),

    previous_7_days AS (
        SELECT
            user_id,
            COUNTIF(kind = 'login') as login_count,
            COUNTIF(kind IN ('assignment_status_updated', 'assignment_review_status_updated')) as assignments_completed
        FROM user_activities
        WHERE timestamp >= @start_14d AND timestamp < @start_7d
        GROUP BY user_id
    ),

    latest_academy AS (
        SELECT user_id, academy_id
        FROM (
            SELECT user_id, academy_id,
                   ROW_NUMBER() OVER(PARTITION BY user_id ORDER BY timestamp DESC) as rn
            FROM user_activities
            WHERE academy_id IS NOT NULL
        )
        WHERE rn = 1
    )

    SELECT
        l7.user_id,
        la.academy_id,
        COALESCE(l7.login_count, 0) as login_count_7d,
        COALESCE(l7.assignments_completed, 0) as assignments_completed_7d,
        TIMESTAMP_DIFF(@end_date, l7.last_activity, DAY) as days_since_last_activity,
        SAFE_DIVIDE(
            COALESCE(l7.login_count, 0) - COALESCE(p7.login_count, 0),
            GREATEST(COALESCE(p7.login_count, 1), 1)
        ) * 100 as login_trend,
        SAFE_DIVIDE(
            COALESCE(l7.assignments_completed, 0) - COALESCE(p7.assignments_completed, 0),
            GREATEST(COALESCE(p7.assignments_completed, 1), 1)
        ) * 100 as assignment_trend

    FROM last_7_days l7
    LEFT JOIN previous_7_days p7 ON l7.user_id = p7.user_id
    LEFT JOIN latest_academy la ON l7.user_id = la.user_id
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ArrayQueryParameter("user_ids", "INT64", user_ids),
            bigquery.ScalarQueryParameter("start_14d", "TIMESTAMP", start_14d.isoformat()),
            bigquery.ScalarQueryParameter("start_7d", "TIMESTAMP", start_7d.isoformat()),
            bigquery.ScalarQueryParameter("end_date", "TIMESTAMP", end_date.isoformat()),
        ]
    )

    results = client.query(query, job_config=job_config).result()

    return {int(row.user_id): dict(row.items()) for row in results}


def generate_churn_alerts(
    user_id: int,
    academy_id: Optional[int],
    risk_level: str,
    metrics: dict,
) -> list[ChurnAlert]:
    """
    Generate churn alerts based on metrics thresholds.

    Args:
        user_id: The user's ID
        academy_id: The academy ID (if any)
        risk_level: The calculated risk level
        metrics: The user's activity metrics

    Returns:
        List of ChurnAlert instances to create
    """
    alerts = []

    # Only generate alerts for HIGH and CRITICAL risk users
    if risk_level not in [ChurnRiskReport.RiskLevel.HIGH, ChurnRiskReport.RiskLevel.CRITICAL]:
        return alerts

    severity = ChurnAlert.Severity.HIGH if risk_level == ChurnRiskReport.RiskLevel.HIGH else ChurnAlert.Severity.CRITICAL

    # Inactivity alert
    days_inactive = metrics.get("days_since_last_activity", 0) or 0
    if days_inactive >= 7:
        alerts.append(
            ChurnAlert(
                user_id=user_id,
                academy_id=academy_id,
                alert_type=ChurnAlert.AlertType.INACTIVITY,
                severity=severity,
                metrics_snapshot=metrics,
            )
        )

    # Payment issues alert
    if metrics.get("has_payment_issues"):
        alerts.append(
            ChurnAlert(
                user_id=user_id,
                academy_id=academy_id,
                alert_type=ChurnAlert.AlertType.PAYMENT_RISK,
                severity=ChurnAlert.Severity.CRITICAL,
                metrics_snapshot=metrics,
            )
        )

    # Engagement drop alert
    login_trend = metrics.get("login_trend", 0) or 0
    if login_trend <= -50:  # 50% or more drop in logins
        alerts.append(
            ChurnAlert(
                user_id=user_id,
                academy_id=academy_id,
                alert_type=ChurnAlert.AlertType.ENGAGEMENT_DROP,
                severity=severity,
                metrics_snapshot=metrics,
            )
        )

    # High frustration alert
    frustration = metrics.get("avg_frustration_score", 0) or 0
    if frustration >= 70:
        alerts.append(
            ChurnAlert(
                user_id=user_id,
                academy_id=academy_id,
                alert_type=ChurnAlert.AlertType.HIGH_FRUSTRATION,
                severity=severity,
                metrics_snapshot=metrics,
            )
        )

    # Trial expiring alert
    sub_status = metrics.get("subscription_status")
    days_until = metrics.get("days_until_renewal")
    if sub_status == "FREE_TRIAL" and days_until is not None and days_until <= 3:
        alerts.append(
            ChurnAlert(
                user_id=user_id,
                academy_id=academy_id,
                alert_type=ChurnAlert.AlertType.TRIAL_EXPIRING,
                severity=ChurnAlert.Severity.HIGH,
                metrics_snapshot=metrics,
            )
        )

    return alerts


class ChurnReport(BaseReport):
    """Churn risk report generator."""

    report_type = "churn"

    def fetch_data(self) -> dict[str, Any]:
        """Fetch all data needed for churn reports."""

        # Get active subscribers
        subscription_filter = {"status__in": ["ACTIVE", "FREE_TRIAL", "PAYMENT_ISSUE"]}

        if self.academy_id:
            # Filter by academy through selected_cohort_set relationship
            subscription_filter["selected_cohort_set__academy_id"] = self.academy_id

        subscriptions = (
            Subscription.objects.filter(**subscription_filter)
            .select_related("user")
            .values("user_id", "status", "next_payment_at", "valid_until")
        )

        user_ids = list(set(s["user_id"] for s in subscriptions))

        if not user_ids:
            self.log("No active subscriptions found", "WARNING")
            return {"activity_metrics": {}, "subscriptions": {}, "user_ids": []}

        self.log(f"Found {len(user_ids)} users with active subscriptions")

        # Batch fetch from BigQuery
        activity_metrics = fetch_activity_metrics_batch(user_ids, self.report_date)

        # Build subscription lookup
        subscription_lookup = {}
        for sub in subscriptions:
            user_id = sub["user_id"]
            if user_id not in subscription_lookup:
                subscription_lookup[user_id] = sub

        return {
            "activity_metrics": activity_metrics,
            "subscriptions": subscription_lookup,
            "user_ids": user_ids,
        }

    def process_data(self, raw_data: dict[str, Any]) -> list[ChurnRiskReport]:
        """Process data into ChurnRiskReport instances."""

        reports = []
        self._alerts = []  # Store alerts for later

        for user_id in raw_data["user_ids"]:
            metrics = raw_data["activity_metrics"].get(user_id, {})
            sub = raw_data["subscriptions"].get(user_id, {})

            # Enrich with subscription data
            metrics["subscription_status"] = sub.get("status")
            metrics["has_payment_issues"] = sub.get("status") == "PAYMENT_ISSUE"

            if sub.get("next_payment_at"):
                days_until = (sub["next_payment_at"].date() - self.report_date).days
                metrics["days_until_renewal"] = days_until

            # Calculate risk
            risk_score, risk_level = calculate_churn_risk(metrics)

            # Get academy_id from metrics or None
            academy_id = metrics.get("academy_id")

            report = ChurnRiskReport(
                user_id=user_id,
                academy_id=academy_id,
                report_date=self.report_date,
                churn_risk_score=risk_score,
                risk_level=risk_level,
                days_since_last_activity=metrics.get("days_since_last_activity") or 0,
                login_count_7d=metrics.get("login_count_7d") or 0,
                login_trend=metrics.get("login_trend") or 0,
                assignments_completed_7d=metrics.get("assignments_completed_7d") or 0,
                assignment_trend=metrics.get("assignment_trend") or 0,
                avg_frustration_score=metrics.get("avg_frustration_score"),
                avg_engagement_score=metrics.get("avg_engagement_score"),
                subscription_status=metrics.get("subscription_status"),
                days_until_renewal=metrics.get("days_until_renewal"),
                has_payment_issues=metrics.get("has_payment_issues", False),
                details=metrics,
            )
            reports.append(report)

            # Generate alerts for high-risk users
            alerts = generate_churn_alerts(user_id, academy_id, risk_level, metrics)
            self._alerts.extend(alerts)

        return reports

    def save_reports(self, reports: list[ChurnRiskReport]) -> int:
        """Bulk save reports with upsert."""

        if not reports:
            return 0

        ChurnRiskReport.objects.bulk_create(
            reports,
            update_conflicts=True,
            unique_fields=["user", "report_date"],
            update_fields=[
                "academy",
                "churn_risk_score",
                "risk_level",
                "days_since_last_activity",
                "login_count_7d",
                "login_trend",
                "assignments_completed_7d",
                "assignment_trend",
                "avg_frustration_score",
                "avg_engagement_score",
                "subscription_status",
                "days_until_renewal",
                "has_payment_issues",
                "details",
            ],
        )

        # Save alerts (ignore conflicts to avoid duplicates)
        if hasattr(self, "_alerts") and self._alerts:
            ChurnAlert.objects.bulk_create(self._alerts, ignore_conflicts=True)
            self.log(f"Created {len(self._alerts)} alerts", "WARNING")

        return len(reports)

