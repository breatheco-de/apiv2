#!/usr/bin/env python
"""
Checks for Cohort User status on ended Cohorts
"""
from breathecode.utils import ScriptNotification
from breathecode.admissions.models import CohortUser
from django.utils import timezone

active_user_on_ended_cohort = CohortUser.objects.filter(
    cohort__stage="ENDED"
).exclude(
    educational_status="ACTIVE"
)
# TODO: use educational_status != ACTIVE, check monitoring to see tests
active_user_on_ended_cohort_list = [
    item.user.email for item in active_user_on_ended_cohort]

active_user_on_ended_cohort_list_names = (
    ", ").join(active_user_on_ended_cohort_list)

if len(active_user_on_ended_cohort_list) > 0:
    raise ScriptNotification(
        f"This users: {active_user_on_ended_cohort_list_names} are active on ended cohorts")

print("Everything up to date")
