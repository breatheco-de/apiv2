"""
Monitoring Reports Package.

This package contains various report generators for platform analytics.
Each report type has its own submodule with:
- models.py: Database models for storing report data
- actions.py: Report generation logic and calculations
- tasks.py: (optional) Async task helpers

Available reports:
- churn: User churn risk assessment and alerts

Usage via management command:
    python manage.py generate_report churn
    python manage.py generate_report churn --date 2024-01-15
    python manage.py generate_report churn --days-back 7
    python manage.py generate_report churn --academy 1
"""

from .base import BaseReport

__all__ = ["BaseReport"]

