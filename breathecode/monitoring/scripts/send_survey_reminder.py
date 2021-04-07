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
# test if the cohort is in this range of dates, 2 tests ending_date y kickoff date, no conseguir cohort
# testear cuando no hay cohort en la base de datos
# testear cuando la data en la base de datos es correcta al menos 1 cohort
cohorts_with_pending_surveys = []

for cohort in cohorts:

    lastest_survey = Survey.objects.filter(
        cohort__id=cohort.id).order_by('sent_at').first()
    # crear test con lista de dos survey index 0,1 y chequear que jale solo el de index 1

    num_weeks = calculate_weeks(
        lastest_survey.sent_at.date(), datetime.now().date())

    if num_weeks > 4:
        cohorts_with_pending_surveys.append(cohort.name)
    # testear un caso que tenga mas de 4 semanas y uno 4 semanas de menos

if len(cohorts_with_pending_surveys) > 0:
    cohort_names = (", ").join(cohorts_with_pending_surveys)
    # cuando tenga al menos dos cohorts que los separe por la ","

    raise ScriptNotification(
        f"There are surveys pending to be sent on theese cohorts {cohort_names}", status='MINOR'
    )

print("No reminders")
