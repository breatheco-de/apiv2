"""
Churn Risk Report Module.

This module provides churn risk assessment for platform users.
It analyzes user activity patterns to predict likelihood of churn.

Key metrics tracked:
- Login frequency and trends
- Assignment completion rates
- Engagement and frustration scores
- Payment status
- Days until subscription renewal

Models:
- ChurnRiskReport: Daily per-user risk assessment
- ChurnAlert: Triggered when users cross risk thresholds
"""

from .models import ChurnAlert, ChurnRiskReport

__all__ = ["ChurnRiskReport", "ChurnAlert"]

