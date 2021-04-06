#!/usr/bin/env python
"""
Reminder for sending surveys to each cohort every 4 weeks
"""
from breathecode.utils import ScriptNotification
from breathecode.feedback.models import Survey
from breathecode.admissions.models import Cohort
from datetime import datetime, date
from django.utils import timezone


def calculate_weeks(date_created, current_date):
    days = abs(date_created-current_date).days
    weeks = days//7
    return weeks


cohorts = Cohort.objects.filter(academy__id=academy.id).exclude(
    ending_date__lt=timezone.now(), kickoff_date__gt=timezone.now())

cohorts_with_pending_surveys = []


for cohort in cohorts:

    lastest_survey = Survey.objects.filter(
        cohort__id=cohort.id).order_by('created_at').first()

    num_weeks = calculate_weeks(
        lastest_survey.created_at.date(), datetime.now().date())

    if num_weeks > 4:
        cohorts_with_pending_surveys.append(cohort.name)

if len(cohorts_with_pending_surveys) > 0:
    cohort_names = (", ").join(cohorts_with_pending_surveys)

    raise ScriptNotification(
        f"There are surveys pending to be sent on theese cohorts {cohort_names}", status='MINOR'
    )

print("No reminders")
