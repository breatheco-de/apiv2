#!/usr/bin/env python
"""
Reminder for sending surveys to each cohort every 4 weeks
"""
from breathecode.utils import ScriptNotification
from breathecode.feedback.models import Survey
from breathecode.admissions.models import Cohort, Academy
from datetime import datetime, date
from django.utils import timezone


def calculate_weeks(date_created, current_date):
    days = abs(date_created - current_date).days
    weeks = days // 7
    return weeks


cohorts = Cohort.objects.filter(academy__id=academy.id).exclude(
    ending_date__lt=timezone.now(),
    kickoff_date__gt=timezone.now()).exclude(never_ends=True)

cohorts_with_pending_surveys = []

if not cohorts:
    print("No cohorts found")

for cohort in cohorts:

    lastest_survey = Survey.objects.filter(
        cohort__id=cohort.id).order_by('sent_at').first()

    if lastest_survey is None:
        cohorts_with_pending_surveys.append(cohort.name)
    else:
        sent_at = cohort.kickoff_date.date()
        if lastest_survey.sent_at is not None:
            sent_at = lastest_survey.sent_at.date()

        num_weeks = calculate_weeks(sent_at, datetime.now().date())
        if num_weeks > 4:
            cohorts_with_pending_surveys.append(cohort.name)

if len(cohorts_with_pending_surveys) > 0:
    cohort_names = ("\n").join(
        ["- " + cohort_name for cohort_name in cohorts_with_pending_surveys])

    raise ScriptNotification(
        f"There are {str(len(cohorts_with_pending_surveys))} surveys pending to be sent on theese cohorts: \n {cohort_names}",
        status='MINOR',
        slug='cohort-have-pending-surveys')

print("No reminders")
