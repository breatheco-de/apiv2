#!/usr/bin/env python
"""
Checks for Cohort status after ending date has passes on cohorts
"""
from breathecode.utils import ScriptNotification
from breathecode.admissions.models import Cohort
from django.utils import timezone

cohorts = Cohort.objects.filter(ending_date__lt=timezone.now())
to_fix_cohort_stage = []

for cohort in cohorts:
    if (cohort.stage is not "ENDED"):
        to_fix_cohort_stage.append(cohort.name)
        raise ScriptNotification(
            f"Theese cohorts {to_fix_cohort_stage} ended but have stage different that ENDED", status='MINOR')

print("Everything up to date")
