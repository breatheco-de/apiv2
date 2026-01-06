# Monitoring Reports - Complete Guide

Complete guide to the Monitoring Reports system for generating analytics and insights about platform usage, user behavior, and business metrics.

## Overview

The Monitoring Reports system provides a modular framework for generating daily analytics reports. Reports are designed to:

- **Reduce BigQuery costs** by pre-computing aggregations once per day
- **Enable fast dashboard queries** by storing results in PostgreSQL
- **Support churn prediction** and risk assessment
- **Enable historical trend analysis** with daily snapshots
- **Scale independently** via management commands on dedicated Heroku dynos

**Location:** `breathecode/monitoring/reports/`

---

## Table of Contents

1. [Architecture](#architecture)
2. [Available Reports](#available-reports)
3. [Running Reports](#running-reports)
4. [Churn Risk Report](#churn-risk-report)
5. [Report Structure](#report-structure)
6. [Adding New Reports](#adding-new-reports)
7. [Best Practices](#best-practices)

---

## Architecture

### Modular Design

Each report type lives in its own submodule:

```
breathecode/monitoring/reports/
├── __init__.py           # Package initialization
├── base.py               # BaseReport abstract class
├── churn/                # Churn risk report
│   ├── __init__.py
│   ├── models.py         # ChurnRiskReport, ChurnAlert models
│   └── actions.py        # ChurnReport class, calculation logic
└── engagement/           # Future: Engagement report
    ├── __init__.py
    ├── models.py
    └── actions.py
```

### Base Report Pattern

All reports extend `BaseReport` which provides:

- `fetch_data()` - Get raw data from BigQuery/database
- `process_data()` - Transform raw data into model instances
- `save_reports()` - Bulk save to database
- `generate()` - Orchestrate the full workflow

### Execution Model

Reports are executed via Django management commands (not Celery tasks) to enable:

- **Flexible scheduling** via cronjobs
- **Dedicated resources** (Performance dynos on Heroku)
- **Long-running queries** without timeout constraints
- **Better error visibility** in command output

---

## Available Reports

### Churn Risk Report

**Purpose:** Predict user churn likelihood based on activity patterns

**Command:** `python manage.py generate_report churn`

**Models:**
- `ChurnRiskReport` - Daily per-user risk assessment
- `ChurnAlert` - Triggered alerts for high-risk users

**Details:** See [Churn Risk Report](#churn-risk-report) section below

---

## Running Reports

### Management Command

The `generate_report` command supports multiple report types:

```bash
python manage.py generate_report {report_type} [options]
```

### Command Options

| Option | Description | Example |
|--------|-------------|---------|
| `report_type` | Type of report (required) | `churn`, `engagement` |
| `--date` | Specific date (YYYY-MM-DD) | `--date 2024-12-15` |
| `--academy` | Filter by academy ID | `--academy 1` |
| `--days-back` | Backfill last N days | `--days-back 30` |
| `--dry-run` | Test without saving | `--dry-run` |
| `--verbosity` | Logging verbosity | `--verbosity 2` |

### Usage Examples

```bash
# Generate yesterday's churn report (default)
python manage.py generate_report churn

# Generate for specific date
python manage.py generate_report churn --date 2024-12-15

# Generate for specific academy
python manage.py generate_report churn --academy 1

# Backfill last 30 days
python manage.py generate_report churn --days-back 30

# Test without saving (dry run)
python manage.py generate_report churn --dry-run

# Verbose output for debugging
python manage.py generate_report churn --verbosity 2
```

### Heroku Scheduler Setup

For daily automated runs:

```bash
# Daily at 2 AM UTC (after midnight data is complete)
heroku run python manage.py generate_report churn --app your-app
```

Or configure via Heroku Scheduler addon:
- **Command:** `python manage.py generate_report churn`
- **Schedule:** Daily at 02:00 UTC
- **Dyno Type:** Performance-L (or Standard-2X for large datasets)

---

## Churn Risk Report

### Overview

The Churn Risk Report analyzes user activity patterns to predict likelihood of subscription cancellation. It generates:

1. **Daily risk scores** (0-100) for each active subscriber
2. **Risk level classifications** (LOW, MEDIUM, HIGH, CRITICAL)
3. **Automated alerts** for users crossing risk thresholds
4. **Historical tracking** for trend analysis

### Risk Calculation

The churn risk score is calculated using weighted signals:

| Signal | Weight | Description |
|--------|--------|-------------|
| **Inactivity** | 25% | Days since last activity (max risk at 14+ days) |
| **Engagement Decay** | 20% | Drop in engagement score vs baseline |
| **Frustration** | 15% | High frustration scores from telemetry |
| **Login Decay** | 15% | Decline in login frequency |
| **Assignment Stall** | 15% | Drop in assignment completion rate |
| **Payment Issues** | 10% | Subscription in PAYMENT_ISSUE status |

### Risk Levels

| Score Range | Level | Description |
|-------------|-------|-------------|
| 0-24 | **LOW** | Healthy engagement, low churn risk |
| 25-49 | **MEDIUM** | Some concerning signals, monitor |
| 50-74 | **HIGH** | Significant risk, intervention recommended |
| 75-100 | **CRITICAL** | Very high risk, immediate action needed |

### Data Sources

The report combines data from:

1. **BigQuery Activity Table** - Login frequency, assignment completions, trends
2. **PostgreSQL Subscriptions** - Payment status, renewal dates
3. **Assignment Telemetry** - Engagement and frustration scores (future)

### Query Strategy

The report uses a **single batch BigQuery query** to fetch metrics for all users simultaneously, minimizing costs:

- Queries last 14 days of activity
- Calculates trends comparing last 7 days vs previous 7 days
- Groups by user for efficient processing
- Filters to active subscribers only

### Models

#### ChurnRiskReport

Stores daily risk assessment per user.

**Key Fields:**
- `user` - ForeignKey to User
- `academy` - ForeignKey to Academy (nullable)
- `report_date` - Date of the report
- `churn_risk_score` - Calculated score (0-100)
- `risk_level` - Classification (LOW/MEDIUM/HIGH/CRITICAL)
- `days_since_last_activity` - Days since last platform activity
- `login_count_7d` - Login count in last 7 days
- `login_trend` - Percentage change vs previous 7 days
- `assignments_completed_7d` - Assignments completed in last 7 days
- `assignment_trend` - Percentage change vs previous 7 days
- `avg_frustration_score` - Average frustration from telemetry (if available)
- `avg_engagement_score` - Average engagement from telemetry (if available)
- `subscription_status` - Current subscription status
- `days_until_renewal` - Days until next payment
- `has_payment_issues` - Boolean flag for payment problems
- `details` - JSONField with full metrics breakdown

**Indexes:**
- `(academy, report_date, risk_level)` - Filter high-risk users by academy
- `(risk_level, report_date)` - Find all high-risk users
- `(-churn_risk_score)` - Sort by risk
- `(report_date, -churn_risk_score)` - Daily leaderboards

**Unique Constraint:** `(user, report_date)` - One report per user per day

#### ChurnAlert

Stores triggered alerts when users cross risk thresholds.

**Key Fields:**
- `user` - ForeignKey to User
- `academy` - ForeignKey to Academy (nullable)
- `alert_type` - Type of alert (INACTIVITY, ENGAGEMENT_DROP, etc.)
- `severity` - Alert severity (LOW/MEDIUM/HIGH/CRITICAL)
- `triggered_at` - When alert was created
- `resolved_at` - When alert was resolved (nullable)
- `action_taken` - Text description of intervention (nullable)
- `metrics_snapshot` - JSONField with metrics at alert time

**Alert Types:**
- `INACTIVITY` - User inactive for 7+ days
- `ENGAGEMENT_DROP` - Login frequency dropped 50%+
- `HIGH_FRUSTRATION` - Frustration score >= 70
- `PAYMENT_RISK` - Subscription in PAYMENT_ISSUE status
- `TRIAL_EXPIRING` - Free trial expiring in 3 days without conversion

**Indexes:**
- `(academy, severity, -triggered_at)` - Find recent critical alerts
- `(user, -triggered_at)` - User alert history
- `(alert_type, -triggered_at)` - Alert type trends

### Usage Examples

#### Generate Report

```bash
# Generate yesterday's report
python manage.py generate_report churn

# Generate for specific academy
python manage.py generate_report churn --academy 1

# Backfill historical data
python manage.py generate_report churn --days-back 90
```

#### Query High-Risk Users

```python
from breathecode.monitoring.reports.churn.models import ChurnRiskReport

# Get all critical risk users from today
critical_users = ChurnRiskReport.objects.filter(
    report_date=date.today(),
    risk_level=ChurnRiskReport.RiskLevel.CRITICAL
).select_related('user', 'academy')

# Get users with increasing risk trend
from django.db.models import F

increasing_risk = ChurnRiskReport.objects.filter(
    academy_id=1,
    report_date__gte=date.today() - timedelta(days=7)
).order_by('user_id', '-report_date').annotate(
    risk_change=F('churn_risk_score') - F('previous_score')
).filter(risk_change__gt=20)
```

#### Query Alerts

```python
from breathecode.monitoring.reports.churn.models import ChurnAlert

# Get unresolved critical alerts
critical_alerts = ChurnAlert.objects.filter(
    academy_id=1,
    severity=ChurnAlert.Severity.CRITICAL,
    resolved_at__isnull=True
).select_related('user').order_by('-triggered_at')
```

---

## Report Structure

### Base Report Interface

All reports must implement the `BaseReport` abstract class:

```python
from breathecode.monitoring.reports.base import BaseReport

class MyReport(BaseReport):
    report_type = "my_report"
    
    def fetch_data(self) -> dict[str, Any]:
        """Fetch raw data from BigQuery/database"""
        pass
    
    def process_data(self, raw_data: dict[str, Any]) -> list[Any]:
        """Transform raw data into model instances"""
        pass
    
    def save_reports(self, reports: list[Any]) -> int:
        """Bulk save to database. Returns count saved."""
        pass
```

### Report Lifecycle

1. **Initialization** - Report instance created with `report_date` and optional `academy_id`
2. **fetch_data()** - Queries BigQuery/PostgreSQL for raw data
3. **process_data()** - Transforms raw data into Django model instances
4. **save_reports()** - Bulk creates/updates reports in database
5. **generate()** - Orchestrates steps 2-4 and handles logging

### Logging

Reports use Django management command's stdout for logging:

```python
self.log("Processing started", "SUCCESS")
self.log("Warning message", "WARNING")
self.log("Error occurred", "ERROR")
```

---

## Adding New Reports

### Step-by-Step Guide

#### 1. Create Report Module

Create directory structure:

```bash
mkdir -p breathecode/monitoring/reports/my_report
touch breathecode/monitoring/reports/my_report/__init__.py
touch breathecode/monitoring/reports/my_report/models.py
touch breathecode/monitoring/reports/my_report/actions.py
```

#### 2. Define Models

Create models in `models.py`:

```python
from django.db import models
from django.contrib.auth.models import User
from breathecode.admissions.models import Academy

class MyReport(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE, null=True)
    report_date = models.DateField(db_index=True)
    metric1 = models.IntegerField()
    metric2 = models.FloatField()
    details = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = [["user", "report_date"]]
        indexes = [
            models.Index(fields=["academy", "report_date"]),
        ]
```

#### 3. Implement Report Logic

Create report class in `actions.py`:

```python
from typing import Any
from breathecode.monitoring.reports.base import BaseReport
from .models import MyReport

class MyReportGenerator(BaseReport):
    report_type = "my_report"
    
    def fetch_data(self) -> dict[str, Any]:
        # Query BigQuery or database
        # Return dict with raw data
        return {"user_ids": [...], "metrics": {...}}
    
    def process_data(self, raw_data: dict[str, Any]) -> list[MyReport]:
        reports = []
        for user_id, metrics in raw_data["metrics"].items():
            reports.append(MyReport(
                user_id=user_id,
                report_date=self.report_date,
                metric1=metrics["metric1"],
                metric2=metrics["metric2"],
                details=metrics,
            ))
        return reports
    
    def save_reports(self, reports: list[MyReport]) -> int:
        MyReport.objects.bulk_create(
            reports,
            update_conflicts=True,
            unique_fields=["user", "report_date"],
            update_fields=["metric1", "metric2", "details"]
        )
        return len(reports)
```

#### 4. Register Report

Add to `generate_report.py`:

```python
from breathecode.monitoring.reports.my_report.actions import MyReportGenerator

REPORT_REGISTRY = {
    "churn": ChurnReport,
    "my_report": MyReportGenerator,  # Add here
}
```

#### 5. Register Models

Add imports to `breathecode/monitoring/models.py`:

```python
from breathecode.monitoring.reports.my_report.models import MyReport

__all__ = [
    # ... existing models
    "MyReport",
]
```

#### 6. Create Migration

```bash
python manage.py makemigrations monitoring --name add_my_report
python manage.py migrate monitoring
```

### Best Practices

1. **Use batch queries** - Fetch all users in one BigQuery query
2. **Use bulk operations** - `bulk_create` with `update_conflicts` for upserts
3. **Store computed metrics** - Pre-calculate aggregations, not raw counts
4. **Index strategically** - Add indexes for common query patterns
5. **Include details JSON** - Store full breakdown for debugging/analysis
6. **Handle nulls gracefully** - Use `COALESCE` in SQL, defaults in Python
7. **Log progress** - Use `self.log()` for visibility during execution

---

## Best Practices

### Cost Optimization

1. **Single Batch Query** - Fetch all users in one BigQuery query, not per-user queries
2. **Partition by Date** - Use BigQuery date partitioning to reduce scan costs
3. **Cluster by User** - Cluster tables by `user_id` for faster filtering
4. **Store Aggregates** - Store computed metrics, not raw activity counts
5. **Archive Old Data** - Move reports older than 1 year to cold storage

### Performance

1. **Use Indexes** - Index on `(academy, report_date, risk_level)` for common queries
2. **Bulk Operations** - Use `bulk_create` instead of individual `save()` calls
3. **Select Related** - Use `select_related()` when querying related models
4. **Limit Date Ranges** - Query reasonable date ranges (last 30-90 days typically)

### Data Quality

1. **Handle Missing Data** - Use `COALESCE` and defaults for null values
2. **Validate Calculations** - Include sanity checks for calculated metrics
3. **Store Raw Details** - Keep full breakdown in `details` JSONField for debugging
4. **Version Schema** - Include `schema_version` field if report structure evolves

### Monitoring

1. **Dry Run First** - Always test with `--dry-run` before production
2. **Monitor Execution Time** - Track how long reports take to complete
3. **Check Error Rates** - Monitor failed report generations
4. **Alert on Failures** - Set up alerts if reports fail to generate

---

## Troubleshooting

### Report Generation Fails

**Issue:** Command exits with error

**Solutions:**
- Check BigQuery credentials and permissions
- Verify date format is valid (YYYY-MM-DD)
- Check database connection
- Review logs with `--verbosity 2`

### Missing Data in Reports

**Issue:** Users missing from report

**Solutions:**
- Verify users have active subscriptions
- Check BigQuery activity data exists for date range
- Verify academy filter isn't excluding users
- Check for data gaps in BigQuery (null academies, etc.)

### Slow Report Generation

**Issue:** Report takes too long to complete

**Solutions:**
- Use Performance dyno (more memory/CPU)
- Reduce date range for backfills
- Check BigQuery query performance
- Optimize database indexes
- Consider breaking into smaller batches

### High BigQuery Costs

**Issue:** Report queries are expensive

**Solutions:**
- Ensure BigQuery table is partitioned by date
- Add clustering by `user_id`
- Review query to ensure it's scanning minimal data
- Use `SELECT` only needed columns
- Cache frequently accessed data

---

## Related Documentation

- [Student Activity API](./Student_Activity.md) - Activity tracking system
- [Supervisors Documentation](../supervisors/quickstart.md) - Automated monitoring system
- [Student Report API](./STUDENT_REPORT.md) - Student data reporting

---

## Future Reports

Planned report types:

- **Engagement Report** - User engagement trends and patterns
- **Revenue Report** - Subscription revenue, churn rates, LTV
- **Cohort Health Report** - Cohort-level metrics and progress
- **Mentorship Report** - Mentorship session utilization and effectiveness

