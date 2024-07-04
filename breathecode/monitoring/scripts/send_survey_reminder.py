#!/usr/bin/env python
"""
Reminder for sending surveys to each cohort every 4 weeks
"""

# flake8: noqa: F821

from breathecode.utils import ScriptNotification
from breathecode.feedback.models import Survey
from breathecode.admissions.models import Cohort
from datetime import timedelta
from django.utils import timezone


def calculate_weeks(date_created, current_date):
    days = abs(date_created - current_date).days
    weeks = days // 7
    return weeks


ACADEMY_ID = academy.id
# For testing only: ACADEMY_ID = 4
TODAY = timezone.now()
TWO_WEEKS_AGO = TODAY - timedelta(weeks=2)
cohorts = Cohort.objects.filter(academy__id=ACADEMY_ID)
# That ended no more than two weeks ago
cohorts = cohorts.filter(ending_date__gte=TWO_WEEKS_AGO, kickoff_date__lte=TODAY)

# exclude cohorts that never end
cohorts = cohorts.exclude(never_ends=True).exclude(stage__in=["DELETED", "INACTIVE"])

cohorts_with_pending_surveys = []

if not cohorts:
    print("No Active cohorts found for this academy")

not_sent = Survey.objects.filter(cohort__academy__id=ACADEMY_ID, cohort__isnull=False, sent_at__isnull=True)
not_sent = [
    f'- {sur.status}: Survey {sur.id} for cohort {sur.cohort.name} <a href="{ADMIN_URL}/v1/feedback/surveys/{sur.cohort.slug}/{sur.id}?location={sur.cohort.academy.slug}">view</a>'
    for sur in not_sent
]
if len(not_sent) > 0:
    not_sent = ("\n").join(not_sent)
else:
    not_sent = "No other surveys have issues"

for cohort in cohorts:
    lastest_survey = (
        Survey.objects.filter(cohort__id=cohort.id, status__in=["SENT", "PARTIAL"], sent_at__isnull=False)
        .order_by("-sent_at")
        .first()
    )

    if lastest_survey is None:
        sent_at = cohort.kickoff_date.date()
        num_weeks = calculate_weeks(sent_at, timezone.now().date())
        if num_weeks > 2:
            cohorts_with_pending_surveys.append(cohort.name + f": No previous survey was found.")
    else:
        sent_at = lastest_survey.sent_at.date()
        num_weeks = calculate_weeks(sent_at, timezone.now().date())
        if num_weeks > 2:
            cohorts_with_pending_surveys.append(
                cohort.name
                + f': Last survey was <a href="{ADMIN_URL}/feedback/surveys/{cohort.slug}/{lastest_survey.id}?location={academy.slug}">{num_weeks} weeks ago</a>'
            )

if len(cohorts_with_pending_surveys) > 0:
    cohort_names = ("\n").join(["- " + cohort_name for cohort_name in cohorts_with_pending_surveys])

    raise ScriptNotification(
        f"There are {str(len(cohorts_with_pending_surveys))} surveys pending to be sent on these cohorts: "
        f"\n {cohort_names}"
        f"\n\n Also, the following surveys have no sent date, you should delete or resolve their issues: \n"
        f"\n {not_sent}",
        status="MINOR",
        title=f"There are {str(len(cohorts_with_pending_surveys))} surveys pending to be sent at {academy.name}",
        slug="cohort-have-pending-surveys",
    )

print("No reminders")
