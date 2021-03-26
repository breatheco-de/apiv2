#!/usr/bin/env python
"""
Reminder for sending surveys to each cohort every 4 weeks
"""
from breathecode.utils import ScriptNotification
from breathecode.feedback.models import Survey
from django.db.models import Q
from datetime import datetime, date

survey_reminders = Survey.objects.filter(cohort__name__contains="Downtown")


def calculate_weeks(date_created, current_date):
    days = abs(date_created-current_date).days
    weeks = days//7
    return weeks


for item in survey_reminders:
    num_weeks = calculate_weeks(
        item.created_at.date(), datetime.now().date())
    if num_weeks > 4:
        raise ScriptNotification(
            f"There are surveys pending to be resend", status='MINOR')

print("No reminders")
